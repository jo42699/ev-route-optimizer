import re

from app.errors import InvalidLocationError
from app.models import Coordinate
from app.providers.openrouteservice import OpenRouteServiceProvider


COORDINATE_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


async def resolve_location(value: str, geocoder: OpenRouteServiceProvider) -> Coordinate:
    match = COORDINATE_RE.match(value)
    if match:
        try:
            return Coordinate(latitude=float(match.group(1)), longitude=float(match.group(2)))
        except ValueError as exc:
            raise InvalidLocationError("Coordinates must be latitude,longitude within valid ranges") from exc
    value = value.strip()
    if not value:
        raise InvalidLocationError("Location cannot be empty")
    return await geocoder.geocode(value)
