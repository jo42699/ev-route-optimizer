from unittest.mock import AsyncMock
from types import SimpleNamespace
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import Settings
from app.models import Coordinate, Journey
from app.providers.openrouteservice import OpenRouteServiceProvider

@pytest.mark.asyncio
async def test_autocomplete_normalizes_coordinates():
    def handler(request):
        assert request.url.path == "/geocode/autocomplete"
        assert request.url.params["text"] == "Oxford"
        return httpx.Response(200, json={"features": [{"geometry": {"coordinates": [-1.25, 51.75]}, "properties": {"label": "Oxford, UK"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(Settings(openrouteservice_api_key="test"), client)
        assert await provider.autocomplete("Oxford") == [{"label": "Oxford, UK", "location": {"latitude": 51.75, "longitude": -1.25}}]

def test_autocomplete_safe_error(monkeypatch):
    from app.errors import ProviderNotConfiguredError
    fake = SimpleNamespace(ors=SimpleNamespace(autocomplete=AsyncMock(side_effect=ProviderNotConfiguredError("Provider not configured"))))
    monkeypatch.setattr("app.api.service", lambda *args: fake)
    response = TestClient(app).get("/api/locations/autocomplete?text=Oxford")
    assert response.status_code == 503
    assert response.json()["detail"] == "Provider not configured"

def test_via_route_uses_three_waypoints(monkeypatch):
    from datetime import datetime, timezone
    origin, stop, destination = Coordinate(latitude=51, longitude=0), Coordinate(latitude=52, longitude=1), Coordinate(latitude=53, longitude=2)
    direct = Journey(origin="51,0", destination="53,2", origin_coordinates=origin, destination_coordinates=destination, route_distance_km=100, distance_label="100 km", estimated_driving_duration_minutes=60, duration_label="60 min", route_geometry={"type": "LineString", "coordinates": [[0,51],[2,53]]}, generated_at=datetime.now(timezone.utc))
    raw = {"geometry": {"type": "LineString", "coordinates": [[0,51],[1,52],[2,53]]}, "distance_km":120, "duration_minutes":80}
    fake = SimpleNamespace(route=AsyncMock(return_value=(direct, {})), ors=SimpleNamespace(route=AsyncMock(return_value=raw)))
    monkeypatch.setattr("app.api.service", lambda *args: fake)
    response = TestClient(app).get("/api/journey/route?origin=51,0&destination=53,2&via=52,1")
    assert response.status_code == 200
    assert response.json()["distance_km"] == 120
    fake.ors.route.assert_awaited_once_with([origin,stop,destination])
