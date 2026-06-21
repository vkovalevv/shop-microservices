from decimal import Decimal
import json
import aio_pika
from aio_pika import ExchangeType
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy import select

from .events import StockReservedEvent
from ..config import get_settings
from ..database import async_session_maker
from ..models import Payment

EXCHANGE_NAME = 'shop.events'
ROUTING_KEY = 'stock.reserved'
QUEUE_NAME = 'payments.stock_reserved'

class Broker:
    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(
            url=get_settings().rabbitmq_url
        )
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
        )
        
        queue = await self._channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange=self._exchange, routing_key=ROUTING_KEY)

        await queue.consume(self._on_message)  

    async def close(self) -> None:
        if self._connection is not None: 
            await self._connection.close()
    
    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process():
            payload = json.loads(message.body)
            event = StockReservedEvent.model_validate(payload)
            async with async_session_maker() as session:
                existing = await session.scalar(select(Payment)
                                                .where(Payment.order_id == event.order_id))
                if existing is not None:
                    return 
                
                success = event.total_amount <= Decimal('10000')

                payment = Payment(order_id=event.order_id, total_amount=event.total_amount,
                                  status='completed' if success else 'failed',)
                session.add(payment)
                await session.commit()

            if success:
                await self.publish('payment.completed', {'order_id':event.order_id})
            else:
                await self.publish('payment.failed', {'order_id':event.order_id})

    async def publish(self, routing_key:str, body:dict) -> None:
        assert self._exchange is not None
        message = aio_pika.Message(
            body=json.dumps(body, default=str).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT  
        )
        await self._exchange.publish(message, routing_key=routing_key)
    
broker = Broker()