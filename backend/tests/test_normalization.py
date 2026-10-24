import json
from pathlib import Path

from app.services.normalize import normalize_ocm


def test_normalization_preserves_missing_live_fields_as_unknown():
    fixture = Path(__file__).parent / "fixtures" / "ocm_station.json"
    station = normalize_ocm(json.loads(fixture.read_text(encoding="utf-8")))
    assert station is not None
    assert station.station_id == "ocm:12"
    assert station.power_kw_max == 150
    assert station.availability.status.value == "unknown"
    assert station.availability.available_connectors is None
    assert station.pricing.price_per_kwh is None
    assert station.data_quality.price_is_verified is False
