from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConnectorType(str, Enum):
    CCS = "CCS"
    CHADEMO = "CHAdeMO"
    TYPE_2 = "Type 2"
    TYPE_1 = "Type 1"
    TESLA = "Tesla"
    GB_T = "GB/T"
    OTHER = "Other"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class SortBy(str, Enum):
    RECOMMENDED = "recommended"
    AVAILABILITY = "availability"
    FASTEST = "fastest"
    CHEAPEST = "cheapest"
    DETOUR = "detour"


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class Address(BaseModel):
    line_1: str | None = None
    line_2: str | None = None
    city: str | None = None
    state_or_province: str | None = None
    postcode: str | None = None
    country: str | None = None
    formatted: str | None = None


class Connector(BaseModel):
    connector_id: str | None = None
    type: str
    power_kw: float | None = Field(default=None, ge=0)
    status: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    available_count: int | None = Field(default=None, ge=0)
    total_count: int | None = Field(default=None, ge=0)


class Pricing(BaseModel):
    currency: str | None = None
    price_per_kwh: float | None = Field(default=None, ge=0)
    unit: str | None = None
    source: str | None = None
    last_updated: datetime | None = None


class Availability(BaseModel):
    status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    available_connectors: int | None = Field(default=None, ge=0)
    total_connectors: int | None = Field(default=None, ge=0)
    observed_at: datetime | None = None
    source: str | None = None
    is_stale: bool = True
    source_status: str | None = None


class StationRoute(BaseModel):
    detour_minutes: float | None = Field(default=None, ge=0)
    detour_distance_km: float | None = Field(default=None, ge=0)
    minutes_from_origin: float | None = Field(default=None, ge=0)
    method: str | None = None


class Prediction(BaseModel):
    probability_available_on_arrival: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    estimated_arrival_at: datetime | None = None
    expected_wait_minutes: float | None = Field(default=None, ge=0)
    model_version: str | None = None
    prediction_basis: str | None = None
    generated_at: datetime | None = None
    underlying_observation_at: datetime | None = None


class Recommendation(BaseModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class Access(BaseModel):
    is_public: bool | None = None
    opening_hours: str | None = None
    access_notes: str | None = None


class DataQuality(BaseModel):
    availability_is_live: bool = False
    price_is_verified: bool = False
    last_updated: datetime | None = None
    warnings: list[str] = Field(default_factory=list)


class Station(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station_id: str
    name: str
    operator: str | None = None
    address: Address = Field(default_factory=Address)
    location: Coordinate
    connectors: list[Connector] = Field(default_factory=list)
    power_kw_max: float | None = Field(default=None, ge=0)
    pricing: Pricing = Field(default_factory=Pricing)
    availability: Availability = Field(default_factory=Availability)
    route: StationRoute = Field(default_factory=StationRoute)
    prediction: Prediction = Field(default_factory=Prediction)
    recommendation: Recommendation | None = None
    amenities: list[str] | None = None
    access: Access = Field(default_factory=Access)
    data_quality: DataQuality = Field(default_factory=DataQuality)


class Journey(BaseModel):
    origin: str
    destination: str
    origin_coordinates: Coordinate
    destination_coordinates: Coordinate
    route_distance_km: float
    distance_label: str
    estimated_driving_duration_minutes: float
    duration_label: str
    route_geometry: dict[str, Any]
    currency: str = "GBP"
    generated_at: datetime


class Filters(BaseModel):
    connector: list[str] = Field(default_factory=list)
    min_power_kw: float | None = None
    max_detour_minutes: float
    sort_by: SortBy
    limit: int


class Summary(BaseModel):
    stations_found: int = Field(ge=0)
    stations_matching_filters: int = Field(ge=0)
    best_station_id: str | None = None


class MapMarker(BaseModel):
    station_id: str
    location: Coordinate
    rank: int | None = None
    availability_status: AvailabilityStatus
    probability_available_on_arrival: float | None = None


class MapData(BaseModel):
    bounds: list[list[float]]
    origin_marker: Coordinate
    destination_marker: Coordinate
    station_markers: list[MapMarker]


class DataQualityResponse(BaseModel):
    freshness: str
    prediction_method: str
    source_availability: dict[str, str]
    warnings: list[str] = Field(default_factory=list)


class RecommendationsResponse(BaseModel):
    journey: Journey
    filters: Filters
    summary: Summary
    recommended_stations: list[Station]
    map: MapData
    data_quality: DataQualityResponse


class RouteResponse(BaseModel):
    origin: Coordinate
    destination: Coordinate
    distance_km: float
    duration_minutes: float
    distance_label: str
    duration_label: str
    geometry: dict[str, Any]
    generated_at: datetime


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    upstreams: dict[str, dict[str, str]]
    generated_at: datetime


class HistoryResponse(BaseModel):
    station_id: str
    available: bool
    source: str | None = None
    observations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MetadataResponse(BaseModel):
    connector_types: list[str]
    sort_options: list[str]
    units: dict[str, str]
    currency_conventions: dict[str, str]
    data_sources: dict[str, dict[str, Any]]
