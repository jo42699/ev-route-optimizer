from app.models import Recommendation, SortBy, Station


def _compatibility(station: Station, connectors: list[str], min_power_kw: float | None) -> bool:
    wanted = {item.casefold() for item in connectors}
    connector_match = not wanted or any(item.type.casefold() in wanted for item in station.connectors)
    power_match = min_power_kw is None or any((not wanted or item.type.casefold() in wanted) and item.power_kw is not None and item.power_kw >= min_power_kw for item in station.connectors)
    return connector_match and power_match


def filter_stations(stations: list[Station], connectors: list[str], min_power_kw: float | None,
                    max_detour_minutes: float) -> list[Station]:
    return [station for station in stations if _compatibility(station, connectors, min_power_kw)
            and station.route.detour_minutes is not None and station.route.detour_minutes <= max_detour_minutes]


def _score(station: Station) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if station.prediction.probability_available_on_arrival is not None:
        score += 0.45 * station.prediction.probability_available_on_arrival
        if station.prediction.probability_available_on_arrival >= 0.8:
            reasons.append("high supported predicted availability")
    if station.route.detour_minutes is not None:
        score += 0.25 * max(0.0, 1.0 - min(station.route.detour_minutes / 30.0, 1.0))
        if station.route.detour_minutes <= 10:
            reasons.append("low verified route detour")
    if station.prediction.expected_wait_minutes is not None:
        score += 0.15 * max(0.0, 1.0 - min(station.prediction.expected_wait_minutes / 30.0, 1.0))
    if station.power_kw_max is not None:
        score += 0.1 * min(station.power_kw_max / 350.0, 1.0)
        if station.power_kw_max >= 100:
            reasons.append("higher published charging power")
    if station.pricing.price_per_kwh is not None and station.data_quality.price_is_verified:
        score += 0.05
        reasons.append("lower cost can be compared from a verified tariff")
    else:
        reasons.append("availability and price remain unverified")
    return min(score, 1.0), reasons


def rank_stations(stations: list[Station], sort_by: SortBy) -> list[Station]:
    scored: list[tuple[Station, float, list[str]]] = []
    for station in stations:
        score, reasons = _score(station)
        scored.append((station, score, reasons))
    if sort_by == SortBy.AVAILABILITY:
        scored.sort(key=lambda item: (item[0].prediction.probability_available_on_arrival is not None,
                                      item[0].prediction.probability_available_on_arrival or -1), reverse=True)
    elif sort_by in (SortBy.FASTEST, SortBy.DETOUR):
        scored.sort(key=lambda item: (item[0].route.detour_minutes is None, item[0].route.detour_minutes if item[0].route.detour_minutes is not None else float("inf")))
    elif sort_by == SortBy.CHEAPEST:
        scored.sort(key=lambda item: (not item[0].data_quality.price_is_verified,
                                      item[0].pricing.price_per_kwh if item[0].pricing.price_per_kwh is not None else float("inf")))
    else:
        scored.sort(key=lambda item: item[1], reverse=True)
    for rank, (station, score, reasons) in enumerate(scored, 1):
        station.recommendation = Recommendation(rank=rank, score=round(score, 4), reasons=reasons)
    return [item[0] for item in scored]
