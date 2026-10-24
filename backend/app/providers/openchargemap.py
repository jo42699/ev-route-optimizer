from typing import Any

import httpx

from app.cache import station_cache
from app.config import Settings
from app.errors import ProviderNotConfiguredError, StationNotFoundError
from app.providers.http import request_json


class OpenChargeMapProvider:
    name = "openchargemap"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.settings.openchargemap_api_key)

    async def search(self, *, latitude: float | None = None, longitude: float | None = None,
                     distance_km: float | None = None, boundingbox: str | None = None,
                     maxresults: int = 50, minpowerkw: float | None = None) -> list[dict[str, Any]]:
        if not self.configured:
            raise ProviderNotConfiguredError("OPENCHARGEMAP_API_KEY is not configured")
        params: dict[str, Any] = {"output": "json", "compact": "false", "verbose": "false", "maxresults": maxresults}
        if latitude is not None and longitude is not None:
            params.update(latitude=latitude, longitude=longitude, distance=distance_km or 25, distanceunit="KM")
        if boundingbox:
            params["boundingbox"] = boundingbox
        if minpowerkw is not None:
            params["minpowerkw"] = minpowerkw
        key = f"ocm:search:{sorted(params.items())}"
        cached = station_cache.get(key)
        if cached is not None:
            return cached
        data = await request_json(self.client, "GET", f"{self.settings.openchargemap_base_url.rstrip('/')}/poi",
                                  params={**params, "key": self.settings.openchargemap_api_key},
                                  headers={"X-API-Key": self.settings.openchargemap_api_key, "User-Agent": "ChargeSmart/1.0"})
        if not isinstance(data, list):
            return []
        return station_cache.set(key, data, self.settings.openchargemap_station_ttl_seconds)

    async def get(self, provider_id: str) -> dict[str, Any]:
        if not self.configured:
            raise ProviderNotConfiguredError("OPENCHARGEMAP_API_KEY is not configured")
        numeric_id = provider_id.removeprefix("ocm:")
        if not numeric_id.isdigit():
            raise StationNotFoundError("Station ID is not a valid Open Charge Map ID")
        key = f"ocm:station:{numeric_id}"
        cached = station_cache.get(key)
        if cached is not None:
            return cached
        data = await request_json(self.client, "GET", f"{self.settings.openchargemap_base_url.rstrip('/')}/poi",
                                  params={"chargepointid": numeric_id, "output": "json", "compact": "false",
                                          "verbose": "true", "key": self.settings.openchargemap_api_key},
                                  headers={"X-API-Key": self.settings.openchargemap_api_key, "User-Agent": "ChargeSmart/1.0"})
        if not isinstance(data, list) or not data:
            raise StationNotFoundError("Charging station was not found")
        return station_cache.set(key, data[0], self.settings.openchargemap_station_ttl_seconds)
