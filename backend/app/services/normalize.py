from datetime import datetime, timezone
from typing import Any

from app.models import Access, Address, Availability, AvailabilityStatus, Connector, Coordinate, DataQuality, Pricing, Station


def _text(value: Any) -> str | None:
    return str(value).strip() if value not in (None, "") else None


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _nested_title(value: Any) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("Title") or value.get("title") or value.get("Name") or value.get("name"))
    return _text(value)


def normalize_ocm(raw: dict[str, Any]) -> Station | None:
    address_info = raw.get("AddressInfo") or raw.get("address_info") or {}
    latitude = address_info.get("Latitude") if address_info.get("Latitude") is not None else address_info.get("latitude")
    longitude = address_info.get("Longitude") if address_info.get("Longitude") is not None else address_info.get("longitude")
    station_id = raw.get("ID") or raw.get("id") or address_info.get("ID")
    if latitude is None or longitude is None or station_id is None:
        return None
    try:
        location = Coordinate(latitude=float(latitude), longitude=float(longitude))
    except (TypeError, ValueError):
        return None
    line_1 = _text(address_info.get("AddressLine1") or address_info.get("address_line_1"))
    line_2 = _text(address_info.get("AddressLine2") or address_info.get("address_line_2"))
    city = _text(address_info.get("Town") or address_info.get("town") or address_info.get("City"))
    state = _text(address_info.get("StateOrProvince") or address_info.get("state_or_province"))
    postcode = _text(address_info.get("Postcode") or address_info.get("postcode"))
    country = _nested_title(address_info.get("Country") or address_info.get("country"))
    parts = [part for part in [line_1, line_2, city, state, postcode, country] if part]
    connectors: list[Connector] = []
    for index, item in enumerate(raw.get("Connections") or []):
        if not isinstance(item, dict):
            continue
        connector_type = _nested_title(item.get("ConnectionType") or item.get("connection_type")) or "Other"
        power = item.get("PowerKW") or item.get("power_kw")
        quantity = item.get("Quantity") or item.get("quantity")
        status = _nested_title(item.get("StatusType") or item.get("status_type"))
        try:
            power = float(power) if power is not None else None
        except (TypeError, ValueError):
            power = None
        try:
            quantity = int(quantity) if quantity is not None else None
        except (TypeError, ValueError):
            quantity = None
        connectors.append(Connector(connector_id=f"ocm:{station_id}:connection:{index}", type=connector_type,
                                    power_kw=power, status=status, quantity=quantity, total_count=quantity))
    powers = [item.power_kw for item in connectors if item.power_kw is not None]
    provider_updated = _parse_time(raw.get("DateLastVerified") or raw.get("DateLastStatusUpdate"))
    warnings = ["Open Charge Map metadata does not establish live occupancy or a verified tariff."]
    return Station(
        station_id=f"ocm:{station_id}",
        name=_text(address_info.get("Title") or raw.get("Title") or f"Charging station {station_id}") or f"Charging station {station_id}",
        operator=_nested_title(raw.get("OperatorInfo") or raw.get("Operator")),
        address=Address(line_1=line_1, line_2=line_2, city=city, state_or_province=state, postcode=postcode,
                        country=country, formatted=", ".join(parts) or None),
        location=location, connectors=connectors, power_kw_max=max(powers) if powers else None,
        pricing=Pricing(), availability=Availability(status=AvailabilityStatus.UNKNOWN, is_stale=True),
        access=Access(is_public=None, opening_hours=None, access_notes=_text(raw.get("UsageType") or raw.get("UsageTypeTitle"))),
        data_quality=DataQuality(availability_is_live=False, price_is_verified=False, last_updated=provider_updated,
                                 warnings=warnings),
    )


def apply_live_data(station: Station, status: dict[str, Any] | None, price: dict[str, Any] | None) -> Station:
    warnings = list(station.data_quality.warnings)
    if status:
        observed = _parse_time(status.get("observed_at"))
        stale = observed is None or (datetime.now(timezone.utc) - observed).total_seconds() > 300
        station.availability = Availability(status=AvailabilityStatus(status.get("status", "unknown")), observed_at=observed,
                                            source="urbanfox", is_stale=stale, source_status=_text(status.get("source_status")))
        station.data_quality.availability_is_live = not stale
        if stale:
            warnings.append("Live status was returned but its observation is stale or lacks a timestamp.")
    else:
        warnings.append("No configured live availability source covers this station; status is unknown.")
    if price and isinstance(price, dict):
        value = price.get("price_per_kwh") or price.get("price")
        currency = price.get("currency")
        try:
            value = float(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        if value is not None and currency:
            station.pricing = Pricing(currency=str(currency), price_per_kwh=value, unit="per kWh", source="urbanfox",
                                      last_updated=_parse_time(price.get("last_updated")))
            station.data_quality.price_is_verified = True
        else:
            warnings.append("Pricing source returned no reliable numeric tariff.")
    else:
        warnings.append("No verified price is available from the configured providers.")
    station.data_quality.warnings = list(dict.fromkeys(warnings))
    station.data_quality.last_updated = station.availability.observed_at or station.data_quality.last_updated
    return station
