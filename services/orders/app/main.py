from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from .routers.orders import router
from .models import Base
from .database import engine
from .messaging.broker import broker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await broker.connect()
    yield
    await broker.close()

app = FastAPI(lifespan=lifespan)

app.include_router(router)
