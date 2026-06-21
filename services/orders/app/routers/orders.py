from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..models import Order, OrderItem
from ..schemas import OrderCreate, OrderRead
from ..clients.products import get_products_client, ProductsClient
from ..messaging.events import OrderItemEvent, OrderCreatedEvent
from ..messaging.broker import broker
router = APIRouter(prefix='/orders', tags=['orders'])


@router.post('', response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_session),
    products: ProductsClient = Depends(get_products_client)
) -> Order:
    order_items: list[OrderItem] = []
    total = Decimal('0')

    for item in payload.items:
        product = await products.get_product(item.product_id)

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')

        if product.stock_quantity - product.reserved_quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Not enough stock quantity'
            )

        order_item = OrderItem(
            product_id=product.id, quantity=item.quantity, price_at_purchase=product.price)

        order_items.append(order_item)

        total += product.price * item.quantity

    order = Order(total_amount=total, items=order_items)
    db.add(order)
    await db.commit()
    await db.refresh(order)

    event = OrderCreatedEvent(
        order_id=order.id,
        total_amount=total,
        items=[
            OrderItemEvent(product_id=item.product_id, quantity=item.quantity)
            for item in order.items
        ]
    )

    await broker.publish('order.created', event.model_dump())
    return order
