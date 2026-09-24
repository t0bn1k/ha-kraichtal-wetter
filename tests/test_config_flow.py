"""Setup, reauth and options flows."""

from __future__ import annotations

import pytest
import voluptuous as vol
from aiohttp import ClientConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import API_KEY, respond_with, setup_entry
from custom_components.kraichtal_wetter.const import DEFAULT_API_URL, DOMAIN


def _coordinator(hass: HomeAssistant, entry: MockConfigEntry):
    return hass.data[DOMAIN][entry.entry_id]["coordinator"]


def _default(result, field: str):
    return next(key.default() for key in result["data_schema"].schema if key == field)


async def test_user_creates_entry(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"key": API_KEY, CONF_SCAN_INTERVAL: 600}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kraichtal Wetter"
    assert result["data"] == {"key": API_KEY, CONF_SCAN_INTERVAL: 600, "api_url": DEFAULT_API_URL}
    assert result["result"].unique_id == DOMAIN


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        ({"status": 401}, "invalid_auth"),
        ({"status": 403}, "invalid_auth"),
        ({"status": 500}, "cannot_connect"),
        ({"exc": ClientConnectionError()}, "cannot_connect"),
        ({"exc": TimeoutError()}, "cannot_connect"),
        ({"json": {"ok": False, "error": "x"}}, "cannot_connect"),
        ({"exc": RuntimeError()}, "unknown"),
    ],
)
async def test_user_rejects_key(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, answer, error: str
) -> None:
    """A key that fails the check is reported on the form, nothing is saved."""
    aioclient_mock.get(DEFAULT_API_URL, **answer)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"key": "typo", CONF_SCAN_INTERVAL: 600}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_user_recovers_after_error(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, api_response) -> None:
    respond_with(aioclient_mock, status=403)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"key": "typo"})
    assert result["errors"] == {"base": "invalid_auth"}

    respond_with(aioclient_mock, json=api_response)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"key": API_KEY})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_rejects_short_interval(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    with pytest.raises(vol.Invalid):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"key": API_KEY, CONF_SCAN_INTERVAL: 299}
        )


async def test_user_single_instance(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """A second setup aborts before it asks the API anything."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"key": API_KEY})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0


async def test_reauth(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, api_response
) -> None:
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    respond_with(aioclient_mock, status=403)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"key": "still-wrong"})
    assert result["errors"] == {"base": "invalid_auth"}
    assert config_entry.data["key"] == API_KEY

    respond_with(aioclient_mock, json=api_response)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"key": "new-key"})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data == {"key": "new-key", "api_url": DEFAULT_API_URL}
    _method, _url, _data, headers = aioclient_mock.mock_calls[-1]
    assert headers == {"X-API-Key": "new-key"}


async def test_options_reload_with_new_interval(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api: AiohttpClientMocker
) -> None:
    """Up to 0.12.0 a new interval waited for the next restart."""
    await setup_entry(hass, config_entry)
    before = _coordinator(hass, config_entry)
    assert before.update_interval.total_seconds() == 300

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 900})
    await hass.async_block_till_done()

    assert config_entry.options == {CONF_SCAN_INTERVAL: 900}
    after = _coordinator(hass, config_entry)
    assert after is not before
    assert after.update_interval.total_seconds() == 900


async def test_options_prefill(hass: HomeAssistant, mock_api: AiohttpClientMocker) -> None:
    """options → data → default, and never below the minimum."""
    for data, options, expected in (
        ({}, {}, 300),
        ({CONF_SCAN_INTERVAL: 600}, {}, 600),
        ({CONF_SCAN_INTERVAL: 600}, {CONF_SCAN_INTERVAL: 900}, 900),
        ({CONF_SCAN_INTERVAL: 60}, {}, 300),
    ):
        entry = MockConfigEntry(domain=DOMAIN, version=2, data={"key": API_KEY, **data}, options=options)
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert _default(result, CONF_SCAN_INTERVAL) == expected, (data, options)
        hass.config_entries.options.async_abort(result["flow_id"])
        await hass.config_entries.async_remove(entry.entry_id)
