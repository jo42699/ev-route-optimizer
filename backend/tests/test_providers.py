import pytest
import httpx

from app.config import Settings
from app.errors import ProviderNotConfiguredError, ProviderUnavailableError
from app.providers.http import request_json
from app.providers.openchargemap import OpenChargeMapProvider


@pytest.mark.asyncio
async def test_missing_openchargemap_key_is_explicit():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ProviderNotConfiguredError):
            await OpenChargeMapProvider(Settings(openchargemap_api_key=None), client).search(latitude=51, longitude=0)


@pytest.mark.asyncio
async def test_provider_http_errors_do_not_leak_upstream_body():
    def handler(request):
        return httpx.Response(500, text="secret upstream stack trace")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ProviderUnavailableError, match="Upstream provider returned an error"):
            await request_json(client, "GET", "https://provider.invalid/status")
