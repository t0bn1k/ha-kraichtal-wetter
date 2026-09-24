"""Setup, unload, stored settings and the one-off entity id migration."""

from __future__ import annotations

import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import API_KEY, setup_entry
from custom_components.kraichtal_wetter.const import DEFAULT_API_URL, DOMAIN


def _entry(hass: HomeAssistant, *, version: int = 2, data=None, options=None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        version=version,
        data=data if data is not None else {"key": API_KEY, "api_url": DEFAULT_API_URL},
        options=options or {},
    )
    entry.add_to_hass(hass)
    return entry


def _interval(hass: HomeAssistant, entry: MockConfigEntry) -> float:
    return hass.data[DOMAIN][entry.entry_id]["coordinator"].update_interval.total_seconds()


async def test_setup_and_unload(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api) -> None:
    await setup_entry(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert set(hass.data[DOMAIN][config_entry.entry_id]) == {"coordinator", "client", "entry"}

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert config_entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.parametrize(
    ("data", "options", "expected"),
    [
        ({}, {}, 300),
        ({CONF_SCAN_INTERVAL: 600}, {}, 600),  # ignored up to 0.12.0
        ({CONF_SCAN_INTERVAL: 600}, {CONF_SCAN_INTERVAL: 900}, 900),
    ],
)
async def test_interval_sources(hass: HomeAssistant, mock_api, data, options, expected: int) -> None:
    entry = _entry(hass, data={"key": API_KEY, **data}, options=options)
    await setup_entry(hass, entry)

    assert _interval(hass, entry) == expected


async def test_interval_below_minimum_is_lifted(
    hass: HomeAssistant, mock_api, caplog: pytest.LogCaptureFixture
) -> None:
    """An entry stored before the minimum was enforced."""
    entry = _entry(hass, options={CONF_SCAN_INTERVAL: 60})
    await setup_entry(hass, entry)

    assert _interval(hass, entry) == 300
    assert "below the 300 s minimum" in caplog.text


@pytest.mark.parametrize("field", ["api_key", "apikey"])
async def test_legacy_key_field(hass: HomeAssistant, mock_api: AiohttpClientMocker, field: str) -> None:
    entry = _entry(hass, data={field: "legacy-key", "api_url": DEFAULT_API_URL})
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    _method, _url, _data, headers = mock_api.mock_calls[0]
    assert headers == {"X-API-Key": "legacy-key"}


async def test_rejected_key_starts_reauth(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, status=403)
    await setup_entry(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]


async def test_api_down_retries_setup(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(DEFAULT_API_URL, status=500)
    await setup_entry(hass, config_entry)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


# --- entity id migration (config entry version 1 → 2) ---------------------------


def _legacy(registry: er.EntityRegistry, entry: MockConfigEntry, platform: str, unique_id: str, object_id: str) -> str:
    return registry.async_get_or_create(
        platform, DOMAIN, unique_id, suggested_object_id=object_id, config_entry=entry
    ).entity_id


def _entity_id(registry: er.EntityRegistry, platform: str, unique_id: str) -> str | None:
    return registry.async_get_entity_id(platform, DOMAIN, unique_id)


async def test_migration_renames_legacy_ids(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_api
) -> None:
    """English ids from 0.5.0 and German ones from before both move to today's names."""
    hass.config.language = "de"
    entry = _entry(hass, version=1)
    _legacy(entity_registry, entry, "sensor", "kraichtal_wetter_temp", "kraichtal_wetter_outdoor_temperature")
    _legacy(entity_registry, entry, "sensor", "kraichtal_wetter_rain", "kraichtal_wetter_niederschlag_aktuell")
    _legacy(entity_registry, entry, "sensor", "kraichtal_wetter_tmax_today", "kraichtal_wetter_max_temperature_today")
    _legacy(entity_registry, entry, "weather", "kraichtal_wetter_forecast", "kraichtal_wetter_forecast")

    await setup_entry(hass, entry)

    assert entry.version == 2
    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_temp") == "sensor.kraichtal_wetter_aussentemperatur"
    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_rain") == (
        "sensor.kraichtal_wetter_station_heute_niederschlag"
    )
    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_tmax_today") == (
        "sensor.kraichtal_wetter_prognose_resttag_tmax"
    )
    assert _entity_id(entity_registry, "weather", "kraichtal_wetter_forecast") == "weather.kraichtal_wetter"


async def test_migration_leaves_user_ids_alone(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_api
) -> None:
    hass.config.language = "de"
    entry = _entry(hass, version=1)
    _legacy(entity_registry, entry, "sensor", "kraichtal_wetter_dewpoint", "mein_taupunkt")

    await setup_entry(hass, entry)

    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_dewpoint") == "sensor.mein_taupunkt"


async def test_migration_runs_once(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_api
) -> None:
    """After the migration a legacy-looking id is the user's choice."""
    hass.config.language = "de"
    entry = _entry(hass, version=1)
    await setup_entry(hass, entry)

    entity_id = _entity_id(entity_registry, "sensor", "kraichtal_wetter_temp")
    entity_registry.async_update_entity(entity_id, new_entity_id="sensor.kraichtal_wetter_outdoor_temperature")
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_temp") == (
        "sensor.kraichtal_wetter_outdoor_temperature"
    )


async def test_current_entry_is_not_migrated(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, mock_api, caplog: pytest.LogCaptureFixture
) -> None:
    """A fresh install (version 2) never renames anything."""
    caplog.set_level(logging.INFO)
    hass.config.language = "de"
    entry = _entry(hass, version=2)
    _legacy(entity_registry, entry, "sensor", "kraichtal_wetter_temp", "kraichtal_wetter_outdoor_temperature")

    await setup_entry(hass, entry)

    assert _entity_id(entity_registry, "sensor", "kraichtal_wetter_temp") == (
        "sensor.kraichtal_wetter_outdoor_temperature"
    )
    assert "Migrating entity id" not in caplog.text
