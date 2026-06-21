from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')

    database_url: str 
    rabbitmq_url: str

@lru_cache
def get_settings():
    return Settings()