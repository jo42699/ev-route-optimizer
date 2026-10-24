# ChargeSmart backend

FastAPI backend for evidence-based EV charging recommendations. It uses Open Charge Map for station metadata and OpenRouteService for geocoding and driving routes. Urban Fox live status/pricing is optional and is only called when a deployment supplies the actual tenant/data-host URL and paths. There is no database or persistent storage; caches are process-local TTL caches.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENCHARGEMAP_API_KEY and OPENROUTESERVICE_API_KEY.
cd backend
python -m uvicorn app.main:app --reload
```

Open interactive documentation at `http://localhost:8000/docs`.

To verify the required provider keys with small read-only requests, run from the repository root:

```powershell
python backend/check_api_keys.py
```

The check prints `OK`, `FAILED`, or `NOT CONFIGURED` for each provider and never prints secret values. It exits with code 0 only when both required providers accept the keys.

Place names are geocoded by OpenRouteService. Coordinate input is accepted as `latitude,longitude`, for example `51.5074,-0.1278`. Driving routes and station detours are calculated through OpenRouteService; the backend does not substitute straight-line distance for driving distance.

Open Charge Map metadata does not provide live occupancy or a verified tariff. Those fields remain `unknown`/`null` unless an explicitly configured live source supplies them. The MVP does not claim an availability probability or expected wait because no permitted historical availability source is configured. This is reflected in `prediction_basis`, `data_quality`, and response warnings.

## API examples

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/metadata
curl "http://localhost:8000/api/journey/route?origin=51.5074,-0.1278&destination=51.4545,-2.5879"
curl "http://localhost:8000/api/journey/recommendations?origin=51.5074,-0.1278&destination=51.4545,-2.5879&connector=CCS&min_power_kw=50&max_detour_minutes=20&sort_by=recommended&limit=10"
curl "http://localhost:8000/api/chargers?latitude=51.5074&longitude=-0.1278&radius_km=25&limit=20"
curl http://localhost:8000/api/chargers/ocm:12345
curl "http://localhost:8000/api/chargers/ocm:12345?origin=51.5074,-0.1278&destination=51.4545,-2.5879&connector=CCS"
curl http://localhost:8000/api/chargers/ocm:12345/history
```

## Provider and data-quality behavior

- Missing API keys produce a clear `503` for endpoints that require that provider; `/api/health` reports the provider as `not_configured`.
- Provider timeouts, rate limits, malformed responses, and authentication failures are translated to safe upstream errors without exposing secrets.
- Station metadata is cached for `OPENCHARGEMAP_STATION_TTL_SECONDS`; routes use `ROUTE_TTL_SECONDS`; live data uses `LIVE_STATUS_TTL_SECONDS`. Timestamps and stale warnings are returned so cached data is not represented as live.
- `/api/chargers/{station_id}/history` returns an explicit unavailable response because no historical source is configured. It never generates synthetic history.
- Map route geometry is GeoJSON `LineString` geometry with `[longitude, latitude]` coordinate order, compatible with Leaflet GeoJSON layers. Station markers reference the same stable `station_id` as the station list and details endpoint.

## Testing

```bash
cd backend
python -m pytest -q tests
```

Tests use local fixtures and provider-shaped payloads only; they do not call production services or require API keys.

## Sources and attribution

Production deployments should show Open Charge Map attribution as required by its terms and respect provider rate limits. Provider documentation used by this implementation: [Open Charge Map API](https://openchargemap.org/develop/api), [OpenRouteService API](https://openrouteservice.org/dev/), and [Urban Fox public chargepoint data access](https://urbanfox.network/public-charge-point-regulations-data-access/).

## ChargeSmart frontend

The Next.js dashboard is in [`frontend/`](frontend/README.md). From that directory, run `npm install` and `npm run dev`, then open http://localhost:5173. Start the existing FastAPI backend separately on port 8000. See the frontend README for environment configuration, data limits, and verification commands.

The dashboard uses backend metadata, recommendations, routes, and station details. Added backend support includes location autocomplete, one intermediate route stop via the optional `via` query parameter, and shortest-detour sorting. Provider credentials remain on the backend.
