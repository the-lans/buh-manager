from typing import Self, cast

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET_KEY = "dev-secret-key"
_DEFAULT_JWT_SECRET_KEY = "dev-jwt-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "local"
    secret_key: str = _DEFAULT_SECRET_KEY

    database_url: str = "sqlite:///./bookkeeper.db"

    google_client_id: str = ""
    google_client_secret: str = ""

    jwt_secret_key: str = _DEFAULT_JWT_SECRET_KEY
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    frontend_url: str = "http://localhost:5173"

    allowed_emails: list[str] = []

    @field_validator("allowed_emails", mode="before")
    @classmethod
    def parse_allowed_emails(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return cast("list[str]", v)

    yandex_s3_bucket: str = ""
    yandex_access_key: str = ""
    yandex_secret_key: str = ""

    app_timezone: str = "Europe/Moscow"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.is_local:
            return self

        errors: list[str] = []

        if not self.secret_key or self.secret_key == _DEFAULT_SECRET_KEY:
            errors.append("secret_key must be set to a non-default value outside local.")
        if not self.jwt_secret_key or self.jwt_secret_key == _DEFAULT_JWT_SECRET_KEY:
            errors.append("jwt_secret_key must be set to a non-default value outside local.")
        if not self.google_client_id or not self.google_client_secret:
            errors.append("Google OAuth credentials must be configured outside local.")
        if not self.yandex_s3_bucket or not self.yandex_access_key or not self.yandex_secret_key:
            errors.append("Yandex S3 credentials must be configured outside local.")

        if errors:
            raise ValueError(" ".join(errors))

        return self


settings = Settings()
