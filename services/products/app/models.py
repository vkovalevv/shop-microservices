from sqlalchemy import String, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from decimal import Decimal

class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = 'products' 

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock_quantity: Mapped[int] = mapped_column(Integer)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, server_default='0')