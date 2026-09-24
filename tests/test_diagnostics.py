"""Diagnostics download: useful for a bug report, never carrying the API key."""

from __future__ import annotations

import json

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .conftest import API_KEY, setup_entry
from custom_components.kraichtal_wetter.const import DEFAULT_API_URL, DOMAIN
from custom_components.kraichtal_wetter.diagnostics import (
    async_get_config_entry_diagnostics,
)


def _entry(hass: HomeAssistant, data: dict) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, version=2, data=data)
    entry.add_to_hass(hass)
    return entry


async def test_contents(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, api_response) -> None:
    await setup_entry(hass, config_entry)

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["entry"]["data"] == {"key": REDACTED, "api_url": DEFAULT_API_URL}
    assert result["request"] == {
        "url": DEFAULT_API_URL,
        "key_in_url": False,
        "sections": ["current", "days", "hours"],
    }
    assert result["coordinator"] == {
        "last_update_success": True,
        "update_interval_seconds": 300,
        "last_exception": None,
    }
    assert result["api"] == api_response
    assert API_KEY not in json.dumps(result)


async def test_key_only_in_stored_url(hass: HomeAssistant, mock_api) -> None:
    """Entries from before 0.4.4: the key exists nowhere but in `api_url`.

    `async_redact_data` only sees field names, so this is the case the value
    sweep exists for.
    """
    entry = _entry(hass, {"api_url": f"{DEFAULT_API_URL}?key={API_KEY}&pretty=1"})
    await setup_entry(hass, entry)
    # The key is only known from the URL, and must still be found in free text.
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator.last_update_success = False
    coordinator.last_exception = UpdateFailed(f"echo of {API_KEY}")

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["request"]["key_in_url"] is True
    assert result["request"]["url"] == f"{DEFAULT_API_URL}?pretty=1"
    assert result["entry"]["data"]["api_url"] == f"{DEFAULT_API_URL}?pretty=1"
    assert result["coordinator"]["last_exception"]["message"] == f"echo of {REDACTED}"
    assert API_KEY not in json.dumps(result)


async def test_legacy_key_field(hass: HomeAssistant, mock_api) -> None:
    entry = _entry(hass, {"apikey": API_KEY, "api_url": DEFAULT_API_URL})
    await setup_entry(hass, entry)

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["data"]["apikey"] == REDACTED
    assert API_KEY not in json.dumps(result)


async def test_key_in_error_message(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api) -> None:
    await setup_entry(hass, config_entry)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    coordinator.last_update_success = False
    coordinator.last_exception = UpdateFailed(f"Update failed: {DEFAULT_API_URL}?key={API_KEY}")

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["coordinator"]["last_exception"] == {
        "type": "UpdateFailed",
        "message": f"Update failed: {DEFAULT_API_URL}?key={REDACTED}",
    }
    assert API_KEY not in json.dumps(result)
