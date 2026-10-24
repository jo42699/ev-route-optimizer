# ChargeSmart frontend

Next.js App Router, TypeScript, Tailwind CSS, Lucide, React Leaflet, and Zod. This folder lives inside the `ev-route-optimizer` Git repository. The workspace-level `frontend` symlink preserves the original entry path.

## Run

```sh
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:5173. In another terminal, run the existing backend:

```sh
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

If creating a Python environment from scratch, install `ev-route-optimizer/requirements.txt` first. The backend normally reads `ev-route-optimizer/.env`. If your provider environment file is instead at the workspace root, pass `--env-file ../../.env` to uvicorn. Never copy provider credentials into the frontend. `BACKEND_API_URL` is server-only and defaults to http://127.0.0.1:8000. The same-origin GET proxy avoids CORS changes.

## Verification

```sh
npm run typecheck
npm test
npm run build
```

Backend: from `ev-route-optimizer/backend`, run `../.venv/bin/python -m pytest -q tests`.

## Architecture and behavior

- `lib/journey-context.tsx`: shared journey, filters, selection, errors, favourites, theme, and stop route. Requests are aborted when superseded. Local storage contains preferences only.
- `lib/api.ts`: schemas matching the actual Pydantic models, safe errors, null-aware formatting, and verified-status gating.
- `components/`: planner, keyboard-accessible autocomplete, recommendations, interactive map, station details, and native modal dialogs.
- `app/api/backend/[...path]`: restricted server-side adapter to existing FastAPI endpoints. No provider logic or secrets live here.
- No fixtures enter the live UI. `tests/journey.json` is an isolated test fixture only.
- Recommendations preserve backend order and rank. Backend requests apply connector, minimum power, detour, and sorting. Available-only, saved-only, and maximum verified GBP tariff filters narrow the returned candidate set; they do not search the entire provider catalogue.
- The default map is an Oxford–London region preview, with no invented stations or route. Search loads real records and geometry. Tiles are configurable via `NEXT_PUBLIC_MAP_TILE_URL`; if changing providers, update map attribution to their required attribution. Default OpenStreetMap tiles use browser caching, visible attribution, and ordinary viewport requests, with no prefetch or offline downloads. Review https://operations.osmfoundation.org/policies/tiles/ before public deployment.
- Add to Route supports one intermediate charging stop via the new optional `via` parameter on the existing route endpoint. Adding another replaces it. Route metrics update, while recommendation detours remain relative to the original journey, explicitly labelled in the UI.
- Backend additions: `/api/locations/autocomplete` forwards to the documented ORS Pelias autocomplete service; `via` extends route calculation using existing ORS waypoint support; `detour` is a metadata-backed sort option. Compatibility now requires power on a compatible connector, and zero-minute detours sort correctly.

## Data limits

Live occupancy and verified tariffs require a configured, permitted Urban Fox source with actual coverage. Predictions and waiting times remain unavailable unless supported by backend data. The fastest sort is explicitly labelled as detour speed; the backend does not estimate charging duration. Station images are branded placeholders because the canonical backend schema has no photograph field. There is no predictive model training or invented performance claim.

Provider documentation: https://giscience.github.io/openrouteservice/api-reference/endpoints/geocoder/ and backend README links. Provider rate limits and coverage depend on the deployment's subscription. Health reports key configuration, not a live provider connectivity probe.

## Verification in the implementation environment

- Backend tests: **13 passed**.
- Frontend Vitest dashboard tests: **6 passed**.
- Full frontend TypeScript check: **passed**.
- Production build: **passed** with `npm run build -- --webpack`.
- Turbopack's production build is blocked in this sandbox because its CSS worker needs to bind a port. Use the Webpack command above in similarly restricted environments.
- Browser layout and live provider flows remain unverified because starting a local server is denied by environment port-binding restrictions.
