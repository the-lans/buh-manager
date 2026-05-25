from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "local"
    secret_key: str = "dev-secret-key"

    database_url: str = "sqlite:///./bookkeeper.db"

    google_client_id: str = ""
    google_client_secret: str = ""

    jwt_secret_key: str = "dev-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    frontend_url: str = "http://localhost:5173"

    allowed_emails: list[str] = []

    yandex_s3_bucket: str = ""
    yandex_access_key: str = ""
    yandex_secret_key: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_local(self) -> bool:
        return self.environment == "local"


settings = Settings()
