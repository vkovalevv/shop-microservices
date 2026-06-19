from pydantic import BaseModel 

class OrderItemEvent(BaseModel):
    product_id: int
    quantity: int 

class OrderCreatedEvent(BaseModel):
    order_id: int
    items: list[OrderItemEvent]