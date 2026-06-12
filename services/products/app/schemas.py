from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=100)
    price: Decimal = Field(..., ge=0)
    stock_quantity: int = Field(..., ge=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    stock_quantity: int
