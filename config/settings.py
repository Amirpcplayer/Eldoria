from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    database_url: str
    redis_url: str
    admin_id: int

    # Limits apply per bot process; keep the aggregate within the DB budget.
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=100)
    db_pool_timeout: int = Field(default=30, ge=1, le=300)
    db_pool_recycle: int = Field(default=1800, ge=60, le=86400)

    # Bound Redis sockets and use finite timeouts for failed connections.
    redis_max_connections: int = Field(default=50, ge=10, le=500)
    redis_socket_timeout: float = Field(default=5.0, gt=0, le=60)
    redis_connect_timeout: float = Field(default=5.0, gt=0, le=60)
    redis_health_check_interval: int = Field(default=30, ge=0, le=3600)

    fanart_payment_info: str = (
        "اطلاعات پرداخت توسط مدیریت اعلام می‌شود."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
