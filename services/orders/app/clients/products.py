import httpx

from ..schemas import ProductInfo
from ..config import get_settings


class ProductsClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def get_product(self, product_id: int) -> ProductInfo | None:
        async with httpx.AsyncClient(
                base_url=self.base_url, timeout=5.0
        ) as client:
            response = await client.get(f'/products/{product_id}')
            if response.status_code == 404:
                return None
            response.raise_for_status()

            return ProductInfo.model_validate(response.json())


def get_products_client() -> ProductsClient:
    return ProductsClient(base_url=get_settings().products_service_url)
