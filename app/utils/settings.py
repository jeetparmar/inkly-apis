from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    docs_url: str
    debug: bool
    api_version: str
    mongo_details: str
    unsplash_url: str
    client_id: str
    gemini_model: str

    class Config:
        env_file = ".env"


settings = Settings()
