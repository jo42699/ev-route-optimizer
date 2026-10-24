from typing import Any

import httpx

from app.cache import live_cache
from app.config import Settings
from app.errors import ProviderUnavailableError


class UrbanFoxProvider:
    """Optional adapter for explicitly configured Urban Fox/OCPI endpoints.

    Urban Fox publishes chargepoint data through OCPI, but endpoint hosts and
    tenant paths are deployment-specific. This adapter never guesses them.
    """

    name = "urbanfox"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.settings.urbanfox_ocpi_base_url and self.settings.urbanfox_locations_path)

    def _url(self, path: str) -> str:
        return f"{self.settings.urbanfox_ocpi_base_url.rstrip('/')}/{path.lstrip('/')}"

    async def _get(self, path: str, cache_key: str) -> Any:
        cached = live_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.configured:
            return None
        headers = {"Accept": "application/json"}
        if self.settings.urbanfox_token:
            headers["Authorization"] = f"Bearer {self.settings.urbanfox_token}"
        try:
            response = await self.client.get(self._url(path), headers=headers)
            response.raise_for_status()
            value = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError("Urban Fox live data is temporarily unavailable") from exc
        return live_cache.set(cache_key, value, self.settings.live_status_ttl_seconds)

    async def enrich(self, station_id: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        path = self.settings.urbanfox_status_path or self.settings.urbanfox_locations_path
        return await self._get(path.replace("{station_id}", station_id), f"urbanfox:{station_id}")

    async def pricing(self, station_id: str) -> dict[str, Any] | None:
        if not self.settings.urbanfox_pricing_path:
            return None
        return await self._get(self.settings.urbanfox_pricing_path.replace("{station_id}", station_id), f"urbanfox:price:{station_id}")

    def status_for(self, raw: dict[str, Any] | None, station_id: str) -> dict[str, Any] | None:
        if not raw or not isinstance(raw, dict):
            return None
        source_status = raw.get("status") or raw.get("Status")
        if isinstance(raw.get("data"), dict):
            source_status = source_status or raw["data"].get("status")
        if not source_status:
            return None
        status = str(source_status).lower()
        if status in {"available", "available_count"}:
            normalized = "available"
        elif status in {"occupied", "charging", "reserved"}:
            normalized = "occupied"
        elif status in {"unavailable", "outoforder", "out_of_order", "faulted"}:
            normalized = "unavailable"
        else:
            normalized = "unknown"
        observed = raw.get("last_updated") or raw.get("last_updated_at") or raw.get("timestamp")
        return {"status": normalized, "source_status": str(source_status), "observed_at": observed,
                "source": "urbanfox", "station_id": station_id}
