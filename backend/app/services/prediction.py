from datetime import datetime, timezone

from app.models import Prediction, Station


def predict_availability(station: Station, arrival_at: datetime) -> Prediction:
    """Only return predictions supported by permitted historical evidence.

    The MVP has no historical occupancy dataset or validated forecasting service,
    so probability and wait time remain null rather than being guessed.
    """
    station.data_quality.warnings.append(
        "Arrival prediction unavailable: no permitted historical or forecasting source is configured."
    )
    return Prediction(estimated_arrival_at=arrival_at, model_version=None,
                      prediction_basis="unavailable_without_historical_availability_data",
                      generated_at=datetime.now(timezone.utc), underlying_observation_at=station.availability.observed_at)
