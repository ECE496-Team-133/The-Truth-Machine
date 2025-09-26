from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Settings(BaseSettings):
    custom_search_api_key: str = Field(validation_alias="CUSTOM_SEARCH_API_KEY")
    custom_search_engine_id: str = Field(validation_alias="CUSTOM_SEARCH_ENGINE_ID")
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
    )


SETTINGS = Settings()
