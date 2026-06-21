import json

import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import update

from ..config import get_settings
from ..messaging.events import OrderCreatedEvent
from ..database import async_session_maker
from ..models import Product

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
                        all_reserved=False
                        break
                
                if all_reserved:
                    await session.commit()
                    await self.publish('stock.reserved', {'order_id':event.order_id})
                else:
                    await session.rollback()
                    await self.publish('stock.reservation_failed', {'order_id': event.order_id})

    async def publish(self, routing_key: str, body:dict):
        assert self._exchange is not None
        message = aio_pika.Message(body=json.dumps(body).encode(),
                                   delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await self._exchange.publish(message, routing_key=routing_key)    

broker = Broker()
