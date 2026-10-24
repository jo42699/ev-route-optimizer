from datetime import datetime, timezone

from app.models import Coordinate, Station
from app.services.prediction import predict_availability


def test_prediction_is_unavailable_without_historical_source():
    station = Station(station_id="x", name="X", location=Coordinate(latitude=0, longitude=0))
    prediction = predict_availability(station, datetime.now(timezone.utc))
    assert prediction.probability_available_on_arrival is None
    assert prediction.expected_wait_minutes is None
    assert prediction.model_version is None
    assert "unavailable" in prediction.prediction_basis
