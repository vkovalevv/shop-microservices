from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from .database import engine
from .models import Base
from .routers.products import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router)
