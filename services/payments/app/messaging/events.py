from decimal import Decimal
from pydantic import BaseModel

class StockReservedEvent(BaseModel):
    order_id: int
    total_amount: Decimal
