from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ChargeSmart API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    request_timeout_seconds: float = Field(default=12.0, gt=0, le=60)
    openchargemap_api_key: str | None = None
    openchargemap_base_url: str = "https://api.openchargemap.io/v3"
    openchargemap_station_ttl_seconds: int = Field(default=900, ge=0)
    openrouteservice_api_key: str | None = None
    openrouteservice_base_url: str = "https://api.openrouteservice.org"
    route_ttl_seconds: int = Field(default=300, ge=0)
    urbanfox_ocpi_base_url: str | None = None
    urbanfox_token: str | None = None
    urbanfox_locations_path: str | None = None
    urbanfox_pricing_path: str | None = None
    urbanfox_status_path: str | None = None
    live_status_ttl_seconds: int = Field(default=60, ge=0)
    route_search_buffer_km: float = Field(default=8.0, gt=0, le=50)
    default_result_limit: int = Field(default=10, ge=1, le=50)
    max_result_limit: int = Field(default=50, ge=1, le=100)
    max_route_candidates: int = Field(default=15, ge=1, le=50)

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origin.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
