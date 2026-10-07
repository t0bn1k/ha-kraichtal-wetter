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
from custom_components.kraichtal_wetter.sensor import SENSOR_TYPES, unique_id


def _entity_id(registry: er.EntityRegistry, key: str) -> str:
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"kraichtal_wetter_{key}")
    assert entity_id is not None, key
    return entity_id


def _state(hass: HomeAssistant, registry: er.EntityRegistry, key: str):
    state = hass.states.get(_entity_id(registry, key))
    assert state is not None, key
    return state


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_every_sensor_shows_its_field(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api, entity_registry: er.EntityRegistry, api_response
) -> None:
    await setup_entry(hass, config_entry)

    for description in SENSOR_TYPES:
        value = api_response[description.section]
        for part in description.key.split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
        state = hass.states.get(_entity_id_for(entity_registry, description))
        assert state is not None, description.key
        assert state.state == str(value), description.key


def _entity_id_for(registry: er.EntityRegistry, description) -> str:
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id(description))
    assert entity_id is not None, description.key
    return entity_id


async def test_daily_forecast_sensors_read_the_right_day(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry, api_response
) -> None:
    """days[0] is today, days[1] tomorrow (API docs) — not the other way round.

    The recorded response has pop and rain at 0 on both days, so distinct
    values are set here to tell the two indices apart.
    """
    api_response["days"][0].update(pop=70, rain=4.2, confidence=55)
    api_response["days"][1].update(pop=40, rain=2.5, confidence=83)
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    assert _state(hass, entity_registry, "days.0.pop").state == "70"
    assert _state(hass, entity_registry, "days.0.pop").attributes["confidence"] == 55
    assert _state(hass, entity_registry, "days.1.pop").state == "40"
    assert _state(hass, entity_registry, "days.1.rain").state == "2.5"
    assert _state(hass, entity_registry, "days.1.tmax").state == "22"
    tmin = _state(hass, entity_registry, "days.1.tmin")
    assert tmin.state == "6"
    assert tmin.attributes["confidence"] == 83


async def test_daily_forecast_sensors_without_tomorrow(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry, api_response
) -> None:
    """A short `days` array leaves tomorrow unknown instead of failing."""
    api_response["days"] = api_response["days"][:1]
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    assert _state(hass, entity_registry, "days.0.pop").state == "0"
    tmin = _state(hass, entity_registry, "days.1.tmin")
    assert tmin.state == "unknown"
    assert "confidence" not in tmin.attributes


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
    assert _entity_id(entity_registry, "days.1.tmin") == "sensor.kraichtal_wetter_prognose_morgen_tmin"
    assert _entity_id(entity_registry, "days.0.pop") == (
        "sensor.kraichtal_wetter_prognose_heute_regenwahrscheinlichkeit"
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
        ("days.0.pop", None),
        ("days.1.tmax", None),
        ("days.1.tmin", None),
        ("days.1.rain", None),
        ("days.1.pop", None),
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
