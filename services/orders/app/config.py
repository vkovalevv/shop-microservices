from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')
    
    rabbitmq_url: str
    database_url: str
    products_service_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
