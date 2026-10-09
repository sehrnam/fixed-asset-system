from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fixed Asset Accounting Workbook"
    environment: str = "development"

    database_url: str = "sqlite:///./fixed_assets.db"

    secret_key: str = "CHANGE_ME_IN_ENV"

    cookie_name: str = "fas_session"
    cookie_secure: bool = False  # True in production HTTPS
    cookie_samesite: str = "lax"
    session_lifetime_hours: int = 12

    cors_origins: str = "http://localhost:5173"

    currency: str = "GHS"

    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 60

    # --- M6a additions: import safety ---
    max_upload_bytes: int = 5_000_000  # 5 MB
    allowed_xlsx_mime_types: str = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
        "application/octet-stream"
    )

    # --- Self-healing / free-tier deployment (v3.0) ---
    # When true, the app on every startup:
    #   - creates tables if missing
    #   - creates the 4 role-based users if missing
    #   - seeds bank assets if the DB is empty
    #   - automatically runs monthly depreciation from the latest existing
    #     record through the current calendar month
    #   - generates monthly PDF reports for any newly-charged months
    #
    # Required on free-tier hosts where the filesystem is ephemeral
    # (Render, Railway, Fly, etc.). Leave false for local development.
    auto_bootstrap: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_xlsx_mime_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_xlsx_mime_types.split(",") if m.strip()]


settings = Settings()