from decimal import Decimal
from datetime import datetime

from sqlalchemy import Numeric, String, BigInteger, DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

class Base(DeclarativeBase):
    pass

class Payment(Base):
    __tablename__ = 'payments'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10,2))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    