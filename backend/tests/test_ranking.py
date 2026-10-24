from app.models import Connector, Coordinate, SortBy, Station, StationRoute
from app.services.ranking import filter_stations, rank_stations


def station(name, connector="CCS", power=150, detour=5):
    return Station(station_id=name, name=name, location=Coordinate(latitude=51, longitude=0),
                   connectors=[Connector(type=connector, power_kw=power)], power_kw_max=power,
                   route=StationRoute(detour_minutes=detour))


def test_filter_excludes_incompatible_connector_and_power():
    assert [item.station_id for item in filter_stations([station("ccs"), station("type2", "Type 2", 22)], ["CCS"], 100, 20)] == ["ccs"]


def test_ranking_is_transparent_when_prediction_and_price_are_missing():
    result = rank_stations([station("one")], SortBy.RECOMMENDED)
    assert result[0].recommendation is not None
    assert result[0].prediction.probability_available_on_arrival is None
    assert any("unverified" in reason for reason in result[0].recommendation.reasons)
