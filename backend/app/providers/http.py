import httpx

from app.errors import ProviderUnavailableError


async def request_json(client: httpx.AsyncClient, method: str, url: str, *, params: dict | None = None,
                       json: dict | None = None, headers: dict[str, str] | None = None) -> dict | list:
    try:
        response = await client.request(method, url, params=params, json=json, headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.TimeoutException as exc:
        raise ProviderUnavailableError("Upstream provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            raise ProviderUnavailableError("Upstream provider authentication failed") from exc
        if exc.response.status_code == 429:
            raise ProviderUnavailableError("Upstream provider rate limit reached") from exc
        raise ProviderUnavailableError("Upstream provider returned an error") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailableError("Upstream provider returned an invalid response") from exc
    if not isinstance(data, (dict, list)):
        raise ProviderUnavailableError("Upstream provider returned an invalid response")
    return data
