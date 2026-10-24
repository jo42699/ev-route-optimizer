from typing import Any

import httpx

from app.cache import route_cache
from app.config import Settings
from app.errors import ProviderNotConfiguredError, ProviderUnavailableError
from app.models import Coordinate
from app.providers.http import request_json


class OpenRouteServiceProvider:
    name = "openrouteservice"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.settings.openrouteservice_api_key)

    async def geocode(self, text: str) -> Coordinate:
        if not self.configured:
            raise ProviderNotConfiguredError("OPENROUTESERVICE_API_KEY is not configured for place-name geocoding")
        data = await request_json(self.client, "GET", f"{self.settings.openrouteservice_base_url.rstrip('/')}/geocode/search",
                                  params={"api_key": self.settings.openrouteservice_api_key, "text": text, "size": 1})
        features = data.get("features", []) if isinstance(data, dict) else []
        if not features or not isinstance(features[0], dict):
            raise ProviderUnavailableError("The geocoding provider found no matching location")
        coords = features[0].get("geometry", {}).get("coordinates", [])
        if not isinstance(coords, list) or len(coords) < 2:
            raise ProviderUnavailableError("The geocoding provider returned no coordinates")
        return Coordinate(latitude=float(coords[1]), longitude=float(coords[0]))

    async def route(self, coordinates: list[Coordinate]) -> dict[str, Any]:
        if not self.configured:
            raise ProviderNotConfiguredError("OPENROUTESERVICE_API_KEY is not configured for routing")
        if len(coordinates) < 2:
            raise ValueError("At least two route coordinates are required")
        key = "ors:route:" + ";".join(f"{c.latitude:.6f},{c.longitude:.6f}" for c in coordinates)
        cached = route_cache.get(key)
        if cached is not None:
            return cached
        data = await request_json(self.client, "POST", f"{self.settings.openrouteservice_base_url.rstrip('/')}/v2/directions/driving-car/geojson",
                                  json={"coordinates": [[c.longitude, c.latitude] for c in coordinates]},
                                  headers={"Authorization": self.settings.openrouteservice_api_key, "Content-Type": "application/json"})
        features = data.get("features", []) if isinstance(data, dict) else []
        if not features:
            raise ProviderUnavailableError("The routing provider returned no route")
        feature = features[0]
        summary = feature.get("properties", {}).get("summary", {})
        try:
            distance_km = float(summary["distance"]) / 1000
            duration_minutes = float(summary["duration"]) / 60
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderUnavailableError("The routing provider returned incomplete route metrics") from exc
        result = {"geometry": feature.get("geometry"), "distance_km": distance_km, "duration_minutes": duration_minutes}
        return route_cache.set(key, result, self.settings.route_ttl_seconds)
