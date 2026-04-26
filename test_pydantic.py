from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class MyConfig(BaseSettings):
    app_env: str = Field(default="dev")
    model_config = SettingsConfigDict(extra="ignore")

os.environ["APP_ENV"] = "prod"
cfg = MyConfig(app_env="staging")
print(f"app_env: {cfg.app_env}")
