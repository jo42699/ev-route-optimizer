"""Live provider credential check for local development.

Run from either the repository root or backend directory:

    python backend/check_api_keys.py
    python check_api_keys.py

The script prints provider status only; it never prints API keys or upstream
response bodies. It performs small read-only requests and should not be used as
an availability monitor.
"""

import asyncio
import sys

import httpx

from app.config import get_settings


TIMEOUT_SECONDS = 15.0


async def check_openchargemap(client: httpx.AsyncClient, settings) -> bool:
    if not settings.openchargemap_api_key:
        print("Open Charge Map: NOT CONFIGURED (set OPENCHARGEMAP_API_KEY)")
        return False
    try:
        response = await client.get(
            f"{settings.openchargemap_base_url.rstrip('/')}/poi",
            params={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "distance": 1,
                "distanceunit": "KM",
                "maxresults": 1,
                "output": "json",
                "compact": "true",
                "key": settings.openchargemap_api_key,
            },
            headers={"X-API-Key": settings.openchargemap_api_key, "User-Agent": "ChargeSmart-key-check/1.0"},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            print("Open Charge Map: FAILED (unexpected response shape)")
            return False
        print("Open Charge Map: OK")
        return True
    except (httpx.HTTPError, ValueError):
        print(f"Open Charge Map: FAILED (HTTP {response.status_code if 'response' in locals() else 'request error'})")
        return False


async def check_openrouteservice(client: httpx.AsyncClient, settings) -> bool:
    if not settings.openrouteservice_api_key:
        print("OpenRouteService: NOT CONFIGURED (set OPENROUTESERVICE_API_KEY)")
        return False
    try:
        response = await client.post(
            f"{settings.openrouteservice_base_url.rstrip('/')}/v2/directions/driving-car/geojson",
            json={"coordinates": [[-0.1278, 51.5074], [-0.1200, 51.5100]]},
            headers={"Authorization": settings.openrouteservice_api_key, "Content-Type": "application/json"},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not body.get("features"):
            print("OpenRouteService: FAILED (unexpected response shape)")
            return False
        print("OpenRouteService: OK")
        return True
    except (httpx.HTTPError, ValueError):
        print(f"OpenRouteService: FAILED (HTTP {response.status_code if 'response' in locals() else 'request error'})")
        return False


async def main() -> int:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        ocm_ok, ors_ok = await asyncio.gather(
            check_openchargemap(client, settings),
            check_openrouteservice(client, settings),
        )
    if ocm_ok and ors_ok:
        print("Required provider key check: PASSED")
        return 0
    print("Required provider key check: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
