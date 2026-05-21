from typing import Literal

from pathlib import Path

import pytz
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = "Asia/Yekaterinburg"
timezone = pytz.timezone(TIMEZONE)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
ENV_DEV_FILE = BASE_DIR / ".env.dev"  # Среда для разработки

load_dotenv(ENV_FILE)

TEMPLATES_DIR = BASE_DIR / "templates"

# Имя основного S3 бакета
S3_BUCKET_NAME = "diocon-tickets-uploads"
S3_BACKUPS_BUCKET_NAME = "diocon-tickets-backups"


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "postgres"
    port: int = 5432
    user: str = "<USER>"
    password: str = "<PASSWORD>"
    db: str = "<DB>"
    driver: Literal["asyncpg"] = "asyncpg"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = "<PASSWORD>"

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class MinIOSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MINIO_")

    access_key_id: str = "<ACCESS_KEY_ID>"
    secret_access_key: str = "<SECRET_ACCESS_KEY>"
    endpoint_url: str = "http://localhost:9900"


class ImgProxySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMGPROXY_")

    host: str = "localhost"
    port: int = 8081
    key: str = "<KEY>"
    salt: str = "<SALT>"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class JWTSettings(BaseSettings):
    algorithm: str = "HS256"
    access_token_expires_in_minutes: int = 15
    refresh_token_expires_in_days: int = 30


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAIL_")

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    default_from_email: str = "diocon@mail.ru"
    support_email: str = "diocon.support@mail.ru"


class RabbitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBIT_")

    host: str = "localhost"
    port: int = 5672
    user: str = "guest"
    password: str = "quest"

    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"


class YandexCloudSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_CLOUD_")

    folder_id: str = "<FOLDER_ID>"
    api_key: str = "<API_KEY>"
    base_url: str = "https://llm.api.cloud.yandex.net/v1"

    access_key_id: str = "<ACCESS_KEY_ID>"
    secret_access_key: str = "<SECRET_ACCESS_KEY>"
    endpoint_url: str = "https://storage.yandexcloud.net/"

    @property
    def gemma_3_27b_it(self) -> str:
        return f"gpt://{self.folder_id}/gemma-3-27b-it/latest"

    @property
    def aliceai_llm(self) -> str:
        return f"gpt://{self.folder_id}/aliceai-llm"

    @property
    def qwen3_235b(self) -> str:
        return f"gpt://{self.folder_id}/qwen3-235b-a22b-fp8/latest"

    @property
    def yandexgpt_rc(self) -> str:
        return f"gpt://{self.folder_id}/yandexgpt/rc"


class LanguageToolSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LANGTOOL_")

    host: str = "localhost"
    port: int = 8010
    language: str = "ru-RU"

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class EmbeddingsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDINGS_")

    base_url: str = "http://localhost:7997/"
    model_name: str = "openai/clip-vit-base-patch32"
    dimensions: int = 512


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "ДИО-Консалт"
    port: int = 8000

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    @property
    def api_url(self) -> str:
        return f"{self.url}/api/v1"


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ADMIN_")

    email: str = "admin@admin.com"
    password: str = "admin"


class Settings(BaseSettings):
    secret_key: str = "<SECRET_KEY>"
    frontend_url: str = "http://localhost:3000"

    app: AppSettings = AppSettings()
    postgres: PostgresSettings = PostgresSettings()
    redis: RedisSettings = RedisSettings()
    minio: MinIOSettings = MinIOSettings()
    imgproxy: ImgProxySettings = ImgProxySettings()
    jwt: JWTSettings = JWTSettings()
    mail: MailSettings = MailSettings()
    rabbit: RabbitSettings = RabbitSettings()
    yandex_cloud: YandexCloudSettings = YandexCloudSettings()
    language_tool: LanguageToolSettings = LanguageToolSettings()
    embeddings: EmbeddingsSettings = EmbeddingsSettings()
    admin: AdminSettings = AdminSettings()


settings = Settings()
