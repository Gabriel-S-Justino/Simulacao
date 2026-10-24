from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env na raiz do repositório (desenvolvimento) ou no diretório atual.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    max_request_bytes: int = 256 * 1024
    database_url: str | None = None
    # False na Vercel: conexões sem pool local (NullPool), adequado a funções serverless.
    database_pooling: bool = True

    # Integrações externas. A chave da NASA fica só no backend; nunca vai ao frontend.
    nasa_api_key: str | None = None
    nasa_api_base_url: str = "https://api.nasa.gov"
    epic_base_url: str = "https://epic.gsfc.nasa.gov"
    eonet_base_url: str = "https://eonet.gsfc.nasa.gov"
    jpl_ssd_api_base_url: str = "https://ssd-api.jpl.nasa.gov"
    jpl_horizons_base_url: str = "https://ssd.jpl.nasa.gov/api/horizons.api"
    gibs_base_url: str = "https://gibs.earthdata.nasa.gov"
    open_notify_base_url: str = "http://api.open-notify.org"
    external_timeout_seconds: float = 10.0
    nasa_cache_ttl_seconds: int = 3600
    iss_update_interval_seconds: int = 15
    # Por quanto tempo um dado em cache pode ser servido como "stale" quando a fonte falha.
    external_max_stale_seconds: int = 7 * 24 * 3600

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
