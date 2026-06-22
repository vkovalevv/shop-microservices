import json

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import update, select

from ..config import get_settings
from ..messaging.events import OrderCreatedEvent
from ..database import async_session_maker
from ..models import Product, Reservation

EXCHANGE_NAME = "shop.events"
QUEUE_NAME = "products.order_created"
ROUTING_KEY = "order.created"


class Broker:
    def __init__(self):
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        queue = await self._channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange=self._exchange, routing_key=ROUTING_KEY)
        await queue.consume(self._on_message)

        pay_ok_queue = await self._channel.declare_queue("products.payment_completed", durable=True)
        await pay_ok_queue.bind(self._exchange, routing_key="payment.completed")
        await pay_ok_queue.consume(self._payment_completed)

        pay_fail_queue = await self._channel.declare_queue("products.payment_failed", durable=True)
        await pay_fail_queue.bind(self._exchange, routing_key="payment.failed")
        await pay_fail_queue.consume(self._payment_failed)

    async def close(self):
        if self._connection is not None:
            await self._connection.close()

    async def _on_message(self, message: AbstractIncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            event = OrderCreatedEvent.model_validate(payload)
            async with async_session_maker() as session:
                all_reserved = True
                for item in event.items:
                    result = await session.execute(
                        update(Product)
                        .where(Product.id == item.product_id)
                        .where(
                            Product.stock_quantity - Product.reserved_quantity
                            >= item.quantity
                        )
                        .values(
                            reserved_quantity=Product.reserved_quantity + item.quantity
                        )
                    )
                    if not result.rowcount:
                        all_reserved = False
                        break

                if all_reserved:
                    for item in event.items:
                        session.add(
                            Reservation(
                                order_id=event.order_id,
                                product_id=item.product_id,
                                quantity=item.quantity,
                            )
                        )
                    await session.commit()
                    await self.publish(
                        "stock.reserved",
                        {
                            "order_id": event.order_id,
                            "total_amount": event.total_amount,
                        },
                    )
                else:
                    await session.rollback()
                    await self.publish(
                        "stock.reservation_failed",
                        {
                            "order_id": event.order_id,
                            "total_amount": event.total_amount,
                        },
                    )

    async def _payment_completed(self, message: AbstractIncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            order_id = payload["order_id"]

            async with async_session_maker() as session:
                reservations = (
                    await session.scalars(
                        select(Reservation).where(
                            Reservation.order_id == order_id,
                            Reservation.status == "reserved",
                        )
                    )
                ).all()

                if not reservations:
                    return

                for reservation in reservations:
                    await session.execute(
                        update(Product)
                        .where(Product.id == reservation.product_id)
                        .values(
                            stock_quantity=Product.stock_quantity
                            - reservation.quantity,
                            reserved_quantity=Product.reserved_quantity
                            - reservation.quantity,
                        )
                    )
                    reservation.status = "commited"

                await session.commit()

    async def _payment_failed(self, message: AbstractIncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            order_id = payload["order_id"]

            async with async_session_maker() as session:
                reservations = await session.scalars(
                    select(Reservation).where(
                        Reservation.order_id == order_id,
                        Reservation.status == "reserved",
                    )
                )

                if not reservations:
                    return

                for reservation in reservations:
                    await session.execute(
                        update(Product)
                        .where(Product.id == reservation.product_id)
                        .values(
                            reserved_quantity=Product.reserved_quantity - reservation.quantity
                        )
                    )
                    reservation.status = "released"
                await session.commit()

    async def publish(self, routing_key: str, body: dict):
        assert self._exchange is not None
        message = aio_pika.Message(
            body=json.dumps(body, default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)


broker = Broker()
