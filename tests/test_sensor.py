"""Sensor states, attributes, statistics classes and the API status sensor."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import respond_with, setup_entry
from custom_components.kraichtal_wetter.const import DOMAIN
from custom_components.kraichtal_wetter.sensor import SENSOR_TYPES


def _entity_id(registry: er.EntityRegistry, key: str) -> str:
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"kraichtal_wetter_{key}")
    assert entity_id is not None, key
    return entity_id


def _state(hass: HomeAssistant, registry: er.EntityRegistry, key: str):
    state = hass.states.get(_entity_id(registry, key))
    assert state is not None, key
    return state


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()


async def test_every_sensor_shows_its_field(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, entity_registry: er.EntityRegistry, api_response
) -> None:
    await setup_entry(hass, config_entry)

    current = api_response["current"]
    for description in SENSOR_TYPES:
        value = current
        for part in description.key.split("."):
            value = value[part]
        assert _state(hass, entity_registry, description.key).state == str(value), description.key


async def test_german_entity_ids(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, entity_registry: er.EntityRegistry
) -> None:
    """IDs come from de.json on a German instance (AGENTS.md)."""
    hass.config.language = "de"
    await setup_entry(hass, config_entry)

    assert _entity_id(entity_registry, "temp") == "sensor.kraichtal_wetter_aussentemperatur"
    assert _entity_id(entity_registry, "rain") == "sensor.kraichtal_wetter_station_heute_niederschlag"
    assert _entity_id(entity_registry, "rain_today") == "sensor.kraichtal_wetter_prognose_resttag_niederschlag"
    assert _entity_id(entity_registry, "station_today.wind_max") == (
        "sensor.kraichtal_wetter_station_heute_wind_max"
    )


async def test_attributes(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, entity_registry: er.EntityRegistry
) -> None:
    await setup_entry(hass, config_entry)

    assert _state(hass, entity_registry, "temp").attributes["source"] == "live"
    assert _state(hass, entity_registry, "station_today.tmax").attributes["time"] == "04:27"
    assert _state(hass, entity_registry, "station_today.tmin").attributes["time"] == "02:13"
    gust = _state(hass, entity_registry, "station_today.gust").attributes
    assert (gust["time"], gust["beaufort"]) == ("03:44", 2)


async def test_missing_attribute_is_left_out(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry, api_response
) -> None:
    api_response["current"]["temp_source"] = None
    del api_response["current"]["station_today"]["gust_bft"]
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    assert "source" not in _state(hass, entity_registry, "temp").attributes
    gust = _state(hass, entity_registry, "station_today.gust").attributes
    assert gust["time"] == "03:44"
    assert "beaufort" not in gust


@pytest.mark.parametrize(
    ("key", "state_class"),
    [
        ("temp", "measurement"),
        ("wind_dir", "measurement_angle"),
        ("rain", "total_increasing"),  # measured, resets at midnight
        ("station_today.tmax", "measurement"),
        # Forecasts: no statistics at all (AGENTS.md, "Messung vs. Prognose").
        ("tmax_today", None),
        ("tmin_today", None),
        ("rain_today", None),
    ],
)
async def test_state_classes(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, entity_registry: er.EntityRegistry,
    key: str, state_class: str | None
) -> None:
    await setup_entry(hass, config_entry)

    assert _state(hass, entity_registry, key).attributes.get("state_class") == state_class


async def test_api_status_reports_outage_and_recovery(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry, api_response
) -> None:
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)
    status = _state(hass, entity_registry, "api_status")
    assert status.state == "ok"
    assert "last_error" not in status.attributes

    respond_with(aioclient_mock, status=500)
    await _refresh(hass, config_entry)

    status = _state(hass, entity_registry, "api_status")
    assert status.state == "HTTP 500: server-side problem at the API"
    assert status.attributes["last_error"] == status.state
    assert _state(hass, entity_registry, "temp").state == STATE_UNAVAILABLE

    respond_with(aioclient_mock, json=api_response)
    await _refresh(hass, config_entry)

    assert _state(hass, entity_registry, "api_status").state == "ok"
    assert _state(hass, entity_registry, "temp").state == "13.1"


async def test_api_status_truncates_long_messages(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry, api_response
) -> None:
    """The state machine rejects states over 255 characters."""
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    message = "x" * 400
    respond_with(aioclient_mock, json={"ok": False, "error": message})
    await _refresh(hass, config_entry)

    status = _state(hass, entity_registry, "api_status")
    assert status.state == message[:255]
    assert status.attributes["last_error"] == message
