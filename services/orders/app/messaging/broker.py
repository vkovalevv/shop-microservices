import json

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import update

from ..models import Order
from ..config import get_settings
from ..database import async_session_maker
EXCHANGE_NAME = "shop.events"


class Broker:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(get_settings().rabbitmq_url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )

        payment_completed_queue = await self._channel.declare_queue('orders.payment_completed', durable=True)
        await payment_completed_queue.bind(self._exchange, routing_key='payment.completed')
        await payment_completed_queue.consume(self._payment_completed)

        payment_failed_queue = await self._channel.declare_queue('orders.payment_failed', durable=True)
        await payment_failed_queue.bind(self._exchange, routing_key='payment.failed')
        await payment_failed_queue.consume(self._payment_failed)
    
    async def _payment_completed(self, message: AbstractIncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            order_id = payload['order_id']
            async with async_session_maker() as session: 
                await session.execute(
                    update(Order)
                    .where(Order.id == order_id)
                    .values(status = 'paid')
                )

                await session.commit()

    async def _payment_failed(self, message: AbstractIncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            order_id = payload['order_id']
            async with async_session_maker() as session:
                await session.execute(
                    update(Order)
                    .where(Order.id == order_id)
                    .values(status = 'cancelled')
                )
                await session.commit()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish(self, routing_key: str, body: dict) -> None:
        assert self._exchange is not None, "Broker is not connected"
        message = aio_pika.Message(
            body=json.dumps(body, default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)


broker = Broker()
