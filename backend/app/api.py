from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.errors import ChargeSmartError, InvalidLocationError, StationNotFoundError
from app.models import (ConnectorType, DataQualityResponse, Filters, HealthResponse, HistoryResponse, MapData,
                        MapMarker, MetadataResponse, RecommendationsResponse, RouteResponse, SortBy, Summary)
from app.providers.openchargemap import OpenChargeMapProvider
from app.services.journey import JourneyService
from app.services.normalize import apply_live_data, normalize_ocm


router = APIRouter(prefix="/api")


async def get_client(settings: Settings = Depends(get_settings)):
    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        yield client


def service(client: httpx.AsyncClient, settings: Settings) -> JourneyService:
    return JourneyService(settings, client)


def parse_connectors(value: str | None) -> list[str]:
    if not value:
        return []
    values = [item.strip() for item in value.split(",") if item.strip()]
    known = {item.value.casefold() for item in ConnectorType}
    unknown = [item for item in values if item.casefold() not in known]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unsupported connector type(s): {', '.join(unknown)}")
    return values


def map_bounds(stations, journey) -> list[list[float]]:
    points = [journey.origin_coordinates, journey.destination_coordinates] + [item.location for item in stations]
    return [[min(item.latitude for item in points), min(item.longitude for item in points)],
            [max(item.latitude for item in points), max(item.longitude for item in points)]]


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)):
    upstreams = {
        "openchargemap": {"status": "configured" if settings.openchargemap_api_key else "not_configured", "purpose": "station metadata"},
        "openrouteservice": {"status": "configured" if settings.openrouteservice_api_key else "not_configured", "purpose": "geocoding and driving routes"},
        "urbanfox": {"status": "configured" if settings.urbanfox_ocpi_base_url and settings.urbanfox_locations_path else "not_configured", "purpose": "optional live status and pricing"},
    }
    core_ready = bool(settings.openchargemap_api_key and settings.openrouteservice_api_key)
    return HealthResponse(status="healthy" if core_ready else "degraded", service="chargesmart", upstreams=upstreams,
                          generated_at=datetime.now(timezone.utc))


@router.get("/journey/route", response_model=RouteResponse)
async def route(origin: Annotated[str, Query(min_length=1)], destination: Annotated[str, Query(min_length=1)],
                via: str | None = None,
                client: httpx.AsyncClient = Depends(get_client), settings: Settings = Depends(get_settings)):
    try:
        journey_service = service(client, settings)
        journey, _ = await journey_service.route(origin, destination)
        if via:
            from app.services.locations import resolve_location
            stop = await resolve_location(via, journey_service.ors)
            raw = await journey_service.ors.route([journey.origin_coordinates, stop, journey.destination_coordinates])
            journey.route_geometry = raw["geometry"]
            journey.route_distance_km = raw["distance_km"]
            journey.estimated_driving_duration_minutes = raw["duration_minutes"]
            from app.services.journey import distance_label, duration_label
            journey.distance_label = distance_label(raw["distance_km"])
            journey.duration_label = duration_label(raw["duration_minutes"])
    except ChargeSmartError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return RouteResponse(origin=journey.origin_coordinates, destination=journey.destination_coordinates,
                         distance_km=journey.route_distance_km, duration_minutes=journey.estimated_driving_duration_minutes,
                         distance_label=journey.distance_label, duration_label=journey.duration_label,
                         geometry=journey.route_geometry, generated_at=journey.generated_at)


@router.get("/journey/recommendations", response_model=RecommendationsResponse)
async def recommendations(origin: Annotated[str, Query(min_length=1)], destination: Annotated[str, Query(min_length=1)],
                           connector: str | None = None, min_power_kw: Annotated[float | None, Query(ge=0)] = None,
                           max_detour_minutes: Annotated[float, Query(ge=0, le=300)] = 20,
                           sort_by: SortBy = SortBy.RECOMMENDED, limit: Annotated[int, Query(ge=1, le=50)] = 10,
                           client: httpx.AsyncClient = Depends(get_client), settings: Settings = Depends(get_settings)):
    try:
        connectors = parse_connectors(connector)
        journey, found_count, stations = await service(client, settings).recommendations(origin, destination, connectors, min_power_kw,
                                                                                           max_detour_minutes, sort_by, limit)
    except HTTPException:
        raise
    except ChargeSmartError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    markers = [MapMarker(station_id=item.station_id, location=item.location,
                         rank=item.recommendation.rank if item.recommendation else None,
                         availability_status=item.availability.status,
                         probability_available_on_arrival=item.prediction.probability_available_on_arrival) for item in stations]
    warnings = sorted({warning for item in stations for warning in item.data_quality.warnings})
    source_availability = {"route": "available", "station_metadata": "available",
                           "live_status": "available" if any(item.data_quality.availability_is_live for item in stations) else "unknown",
                           "pricing": "available" if any(item.data_quality.price_is_verified for item in stations) else "unknown"}
    prediction_methods = {item.prediction.prediction_basis for item in stations if item.prediction.prediction_basis}
    return RecommendationsResponse(
        journey=journey,
        filters=Filters(connector=connectors, min_power_kw=min_power_kw, max_detour_minutes=max_detour_minutes, sort_by=sort_by, limit=limit),
        summary=Summary(stations_found=found_count, stations_matching_filters=len(stations), best_station_id=stations[0].station_id if stations else None),
        recommended_stations=stations,
        map=MapData(bounds=map_bounds(stations, journey), origin_marker=journey.origin_coordinates,
                    destination_marker=journey.destination_coordinates, station_markers=markers),
        data_quality=DataQualityResponse(
            freshness="Station metadata is cached according to the configured TTL; live data is only live when source and timestamp support it.",
            prediction_method=", ".join(sorted(prediction_methods)) if prediction_methods else "unavailable",
            source_availability=source_availability, warnings=warnings),
    )


@router.get("/chargers")
async def chargers(latitude: float | None = Query(default=None, ge=-90, le=90), longitude: float | None = Query(default=None, ge=-180, le=180),
                   radius_km: Annotated[float, Query(gt=0, le=100)] = 25, bbox: str | None = None,
                   limit: Annotated[int, Query(ge=1, le=100)] = 50, offset: Annotated[int, Query(ge=0)] = 0,
                   client: httpx.AsyncClient = Depends(get_client), settings: Settings = Depends(get_settings)):
    if bbox is None and (latitude is None or longitude is None):
        raise HTTPException(400, "Provide latitude and longitude, or bbox")
    if bbox is not None and (latitude is not None or longitude is not None):
        raise HTTPException(400, "Use either bbox or latitude/longitude, not both")
    try:
        raw = await OpenChargeMapProvider(settings, client).search(latitude=latitude, longitude=longitude, distance_km=radius_km,
                                                                    boundingbox=bbox, maxresults=min(limit + offset, settings.max_result_limit))
    except ChargeSmartError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    stations = [item for item in (normalize_ocm(raw_item) for raw_item in raw) if item is not None]
    return {"stations": stations[offset:offset + limit], "total": len(stations), "offset": offset, "limit": limit,
            "source": "openchargemap", "warnings": ["Live status and verified pricing are not included by Open Charge Map metadata."]}


@router.get("/chargers/{station_id}")
async def charger_detail(station_id: str, origin: str | None = None, destination: str | None = None,
                         connector: str | None = None, min_power_kw: float | None = Query(default=None, ge=0),
                         client: httpx.AsyncClient = Depends(get_client), settings: Settings = Depends(get_settings)):
    try:
        raw = await OpenChargeMapProvider(settings, client).get(station_id)
        station = normalize_ocm(raw)
        if station is None:
            raise StationNotFoundError("Station has no usable coordinates")
        journey_service = service(client, settings)
        live = await journey_service.urbanfox.enrich(station.station_id)
        apply_live_data(station, journey_service.urbanfox.status_for(live, station.station_id),
                        await journey_service.urbanfox.pricing(station.station_id))
        if (origin is None) != (destination is None):
            raise InvalidLocationError("origin and destination must be supplied together")
        if origin and destination:
            journey, base = await journey_service.route(origin, destination)
            await journey_service.candidate_route(journey.origin_coordinates, journey.destination_coordinates, station, base)
            from app.services.prediction import predict_availability
            station.prediction = predict_availability(station, datetime.now(timezone.utc) + timedelta(minutes=station.route.minutes_from_origin or 0))
        return station
    except ChargeSmartError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc


@router.get("/chargers/{station_id}/history", response_model=HistoryResponse)
async def charger_history(station_id: str):
    return HistoryResponse(station_id=station_id, available=False,
                           warnings=["No permitted upstream historical availability source is configured; history was not fabricated."])


@router.get("/metadata", response_model=MetadataResponse)
async def metadata():
    return MetadataResponse(connector_types=[item.value for item in ConnectorType],
                            sort_options=[item.value for item in SortBy],
                            units={"distance": "km", "duration": "minutes", "power": "kW", "price": "currency per kWh"},
                            currency_conventions={"default_display_currency": "GBP", "note": "Provider currency is preserved; no conversion is performed."},
                            data_sources={"openchargemap": {"metadata": True, "live_availability": False, "pricing": False},
                                          "openrouteservice": {"routing": True, "geocoding": True},
                                          "urbanfox": {"live_availability": "optional_configured", "pricing": "optional_configured", "history": False}})


@router.get("/locations/autocomplete")
async def autocomplete(text: Annotated[str, Query(min_length=3, max_length=200)],
                       client: httpx.AsyncClient = Depends(get_client), settings: Settings = Depends(get_settings)):
    try:
        return {"suggestions": await service(client, settings).ors.autocomplete(text)}
    except ChargeSmartError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
