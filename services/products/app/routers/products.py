from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..schemas import ProductRead, ProductCreate
from ..database import get_session
from ..models import Product

router = APIRouter(prefix='/products', tags=['products'])


@router.post('', response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_session),

):
    product = Product(**payload.model_dump())

    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product


@router.get('', response_model=list[ProductRead])
async def read_products(db: AsyncSession = Depends(get_session)):
    products_result = await db.execute(select(Product))
    products = products_result.scalars().all()

    return products


@router.get('/{product_id}', response_model=ProductRead)
async def read_product(product_id: int,
                       db: AsyncSession = Depends(get_session)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='product not found')

    return product
