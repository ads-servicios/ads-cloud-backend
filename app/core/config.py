from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ads-cloud-system"
    app_version: str = "0.1.0"
    app_description: str = "ADS Cloud System API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_docs_url: str = "/docs"
    app_redoc_url: str = "/redoc"
    app_openapi_url: str = "/openapi.json"

    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "ads_cloud"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    email_provider: str = "smtp"
    aws_region: str = "eu-north-1"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    contact_email_to: str = "ads.serviciosintegrales@gmail.com"
    contact_email_from: str = "ads.serviciosintegrales@gmail.com"
    contact_public_website_url: str = "http://localhost:3000"
    contact_footer_email: str = "ads.serviciosintegrales@gmail.com"
    contact_footer_website: str = "https://ads-inversiones.es/"
    contact_confirmation_subject: str = "RE: confirmacion de solicitud"
    cors_origins: str = (
      "http://localhost:3000,http://127.0.0.1:3000,"
      "http://localhost:3001,http://127.0.0.1:3001"
  )

    jwt_secret: str = "dev-only-change-me-use-32b-min-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""

    web_vehicles_s3_bucket: str = ""
    web_vehicles_s3_prefix: str = "images/stock"
    # Optional CDN/site origin for browser reads (e.g. https://ads-inversiones.es).
    # If empty and a bucket is set, list/detail responses use short-lived S3 presigned GET URLs.
    web_vehicles_public_media_base_url: str = ""
    web_vehicles_s3_presign_expires: int = 3600

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> str:
        if isinstance(value, list):
            return ",".join(value)
        return str(value)

    @field_validator("email_provider")
    @classmethod
    def normalize_email_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"smtp", "ses"}:
            raise ValueError("email_provider must be 'smtp' or 'ses'")
        return normalized

    @property
    def is_development(self) -> bool:
        return self.app_env.strip().lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @staticmethod
    def _optional_path(value: str) -> str | None:
        stripped = value.strip()
        return stripped if stripped else None

    @property
    def resolved_docs_url(self) -> str | None:
        """Swagger UI path, or None when disabled (PRO or blank env)."""
        if self.is_production:
            return None
        return self._optional_path(self.app_docs_url)

    @property
    def resolved_redoc_url(self) -> str | None:
        if self.is_production:
            return None
        return self._optional_path(self.app_redoc_url)

    @property
    def resolved_openapi_url(self) -> str | None:
        if self.is_production:
            return None
        return self._optional_path(self.app_openapi_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_not_placeholder_in_prod(cls, value: str, info: ValidationInfo) -> str:
        secret = value.strip()
        env = str(info.data.get("app_env", "development")).strip().lower()
        if env != "development" and (not secret or secret.startswith("dev-only-change-me")):
            raise ValueError("jwt_secret must be set to a strong value outside development")
        return secret


settings = Settings()
