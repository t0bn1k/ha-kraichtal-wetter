"""The HTTP client: request shape, key handling and error mapping."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientConnectionError, ContentTypeError
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import API_KEY
from custom_components.kraichtal_wetter.const import DEFAULT_API_URL
from custom_components.kraichtal_wetter.coordinator import (
    KraichtalWetterClient,
    _split_api_key,
)


def _client(hass: HomeAssistant, url: str = DEFAULT_API_URL, key: str | None = API_KEY):
    return KraichtalWetterClient(url, key, async_get_clientsession(hass))


def _only_request(aioclient_mock: AiohttpClientMocker):
    assert aioclient_mock.call_count == 1
    _method, url, _data, headers = aioclient_mock.mock_calls[0]
    return url, headers or {}


async def test_request_shape(hass: HomeAssistant, mock_api: AiohttpClientMocker, api_response) -> None:
    """Key in the header, never in the URL; only the sections we read."""
    assert await _client(hass).async_update() == api_response

    url, headers = _only_request(mock_api)
    assert headers == {"X-API-Key": API_KEY}
    assert url.query == {"section": "current,days,hours"}
    assert API_KEY not in str(url)


@pytest.mark.parametrize("param", ["key", "api_key", "apikey"])
async def test_key_in_configured_url_moves_to_header(
    hass: HomeAssistant, mock_api: AiohttpClientMocker, param: str
) -> None:
    """Entries from before 0.4.4 carry the key in the URL."""
    await _client(hass, f"{DEFAULT_API_URL}?{param}=from-url&pretty=1", key=None).async_update()

    url, headers = _only_request(mock_api)
    assert headers == {"X-API-Key": "from-url"}
    assert "from-url" not in str(url)
    assert url.query["pretty"] == "1"


async def test_explicit_key_wins_over_url_key(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    await _client(hass, f"{DEFAULT_API_URL}?key=from-url").async_update()

    url, headers = _only_request(mock_api)
    assert headers == {"X-API-Key": API_KEY}
    assert "from-url" not in str(url)


def test_split_api_key() -> None:
    assert _split_api_key(f"{DEFAULT_API_URL}?key=abc&x=1") == (f"{DEFAULT_API_URL}?x=1", "abc")
    assert _split_api_key(DEFAULT_API_URL) == (DEFAULT_API_URL, None)


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_failure(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture, status: int
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, status=status)

    with pytest.raises(ConfigEntryAuthFailed):
        await _client(hass).async_update()
    assert [r.levelno for r in caplog.records] == [logging.WARNING]


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, "HTTP 400: malformed request"),
        (404, "HTTP 404: unknown section requested"),
        (405, "HTTP 405: method not allowed (the API only accepts GET)"),
        (500, "HTTP 500: server-side problem at the API"),
        (502, "HTTP error 502"),
    ],
)
async def test_http_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int, message: str
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, status=status)

    with pytest.raises(UpdateFailed) as err:
        await _client(hass).async_update()
    assert str(err.value) == message


@pytest.mark.parametrize(
    ("exc", "message"),
    [
        (ClientConnectionError("down"), "Update failed: down"),
        (TimeoutError(), "Update failed: "),
        (
            ContentTypeError(MagicMock(real_url=DEFAULT_API_URL), (), status=200, message="text/html"),
            "API returned no JSON",
        ),
    ],
)
async def test_transport_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, exc: Exception, message: str
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, exc=exc)

    with pytest.raises(UpdateFailed) as err:
        await _client(hass).async_update()
    assert str(err.value) == message


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"ok": False, "error": "Unbekannte Sektion: foo"}, "Unbekannte Sektion: foo"),
        ({"ok": False}, "API returned an unsuccessful response"),
        (["not", "a", "dict"], "API returned an unexpected payload"),
    ],
)
async def test_unusable_payload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, payload: object, message: str
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, json=payload)

    with pytest.raises(UpdateFailed) as err:
        await _client(hass).async_update()
    assert str(err.value) == message


@pytest.mark.parametrize(
    "answer",
    [{"status": 500}, {"exc": ClientConnectionError("down")}, {"json": {"ok": False}}],
)
async def test_failures_do_not_log_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture, answer
) -> None:
    """The coordinator reports outage and recovery itself — once each.

    An error logged here would repeat at every scan_interval for the whole
    outage.
    """
    aioclient_mock.get(DEFAULT_API_URL, **answer)

    with pytest.raises(UpdateFailed):
        await _client(hass).async_update()
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.parametrize(
    "answer",
    [{"status": 403}, {"status": 500}, {"exc": ClientConnectionError("down")}],
)
async def test_key_never_logged(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture, answer
) -> None:
    caplog.set_level(logging.DEBUG)
    aioclient_mock.get(DEFAULT_API_URL, **answer)

    with pytest.raises((UpdateFailed, ConfigEntryAuthFailed)) as err:
        await _client(hass, f"{DEFAULT_API_URL}?key={API_KEY}", key=None).async_update()
    assert API_KEY not in caplog.text
    assert API_KEY not in str(err.value)
    assert err.value.__cause__ is None
