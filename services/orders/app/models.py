from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import (DeclarativeBase,
                            mapped_column, Mapped, relationship)
from sqlalchemy import (Integer, String, Numeric, ForeignKey, DateTime, func)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(
        String, default='pending', nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    items: Mapped[list['OrderItem']] = relationship(back_populates='order', cascade='all, delete-orphan',
                                                    lazy='selectin')


class OrderItem(Base):
    __tablename__ = 'order_items'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey('orders.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int]
    price_at_purchase: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    order: Mapped['Order'] = relationship(back_populates='items')