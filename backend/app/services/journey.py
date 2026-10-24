import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.config import Settings
from app.models import Journey, Station
from app.providers.openchargemap import OpenChargeMapProvider
from app.providers.openrouteservice import OpenRouteServiceProvider
from app.providers.urbanfox import UrbanFoxProvider
from app.services.locations import resolve_location
from app.services.normalize import apply_live_data, normalize_ocm
from app.services.prediction import predict_availability
from app.services.ranking import filter_stations, rank_stations


def distance_label(km: float) -> str:
    return f"{km:.1f} km"


def duration_label(minutes: float) -> str:
    total = max(0, round(minutes))
    hours, mins = divmod(total, 60)
    return f"{hours} hr {mins} min" if hours else f"{mins} min"


class JourneyService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self.ocm = OpenChargeMapProvider(settings, client)
        self.ors = OpenRouteServiceProvider(settings, client)
        self.urbanfox = UrbanFoxProvider(settings, client)

    async def resolve_pair(self, origin: str, destination: str):
        return await asyncio.gather(resolve_location(origin, self.ors), resolve_location(destination, self.ors))

    async def route(self, origin: str, destination: str):
        origin_coord, destination_coord = await self.resolve_pair(origin, destination)
        raw = await self.ors.route([origin_coord, destination_coord])
        generated = datetime.now(timezone.utc)
        journey = Journey(origin=origin, destination=destination, origin_coordinates=origin_coord,
                          destination_coordinates=destination_coord, route_distance_km=raw["distance_km"],
                          distance_label=distance_label(raw["distance_km"]),
                          estimated_driving_duration_minutes=raw["duration_minutes"],
                          duration_label=duration_label(raw["duration_minutes"]),
                          route_geometry=raw["geometry"], generated_at=generated)
        return journey, raw

    async def candidate_route(self, origin, destination, station: Station, base: dict) -> None:
        origin_station = await self.ors.route([origin, station.location])
        station_destination = await self.ors.route([station.location, destination])
        station.route.detour_minutes = max(0.0, origin_station["duration_minutes"] + station_destination["duration_minutes"] - base["duration_minutes"])
        station.route.detour_distance_km = max(0.0, origin_station["distance_km"] + station_destination["distance_km"] - base["distance_km"])
        station.route.minutes_from_origin = origin_station["duration_minutes"]
        station.route.method = "OpenRouteService origin→station plus station→destination minus direct route"

    async def recommendations(self, origin: str, destination: str, connectors: list[str], min_power_kw: float | None,
                              max_detour_minutes: float, sort_by, limit: int):
        journey, base = await self.route(origin, destination)
        route_coords = journey.route_geometry.get("coordinates", []) if isinstance(journey.route_geometry, dict) else []
        lats = [float(item[1]) for item in route_coords if isinstance(item, list) and len(item) >= 2]
        lons = [float(item[0]) for item in route_coords if isinstance(item, list) and len(item) >= 2]
        if not lats or not lons:
            lats = [journey.origin_coordinates.latitude, journey.destination_coordinates.latitude]
            lons = [journey.origin_coordinates.longitude, journey.destination_coordinates.longitude]
        buffer_deg_lat = self.settings.route_search_buffer_km / 111.0
        buffer_deg_lon = self.settings.route_search_buffer_km / 80.0
        boundingbox = f"({min(lats)-buffer_deg_lat},{min(lons)-buffer_deg_lon}),({max(lats)+buffer_deg_lat},{max(lons)+buffer_deg_lon})"
        raw_stations = await self.ocm.search(boundingbox=boundingbox, maxresults=min(self.settings.max_result_limit, limit * 4), minpowerkw=min_power_kw)
        normalized = [normalize_ocm(item) for item in raw_stations]
        stations = [item for item in normalized if item is not None][: self.settings.max_route_candidates]

        async def enrich(station: Station) -> Station:
            try:
                await self.candidate_route(journey.origin_coordinates, journey.destination_coordinates, station, base)
                raw_status = await self.urbanfox.enrich(station.station_id)
                apply_live_data(station, self.urbanfox.status_for(raw_status, station.station_id),
                                await self.urbanfox.pricing(station.station_id))
                arrival = datetime.now(timezone.utc) + timedelta(minutes=station.route.minutes_from_origin or 0)
                station.prediction = predict_availability(station, arrival)
            except Exception as exc:
                station.data_quality.warnings.append("Route or live enrichment was unavailable for this station.")
                station.data_quality.warnings.append(type(exc).__name__)
            return station

        enriched = await asyncio.gather(*(enrich(item) for item in stations))
        matching = filter_stations(enriched, connectors, min_power_kw, max_detour_minutes)
        return journey, len(stations), rank_stations(matching, sort_by)[:limit]
