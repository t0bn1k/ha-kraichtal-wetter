"""Weather entity: current conditions, daily and hourly forecast, icon table."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.components import weather
from homeassistant.core import HomeAssistant

from .conftest import respond_with, setup_entry
from custom_components.kraichtal_wetter import weather as kw_weather
from custom_components.kraichtal_wetter.const import DOMAIN

ENTITY_ID = "weather.kraichtal_wetter"


async def _forecast(hass: HomeAssistant, kind: str) -> list[dict]:
    response = await hass.services.async_call(
        weather.DOMAIN,
        weather.SERVICE_GET_FORECASTS,
        {"entity_id": ENTITY_ID, "type": kind},
        blocking=True,
        return_response=True,
    )
    return response[ENTITY_ID]["forecast"]


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.data[DOMAIN][entry.entry_id]["coordinator"].async_refresh()
    await hass.async_block_till_done()


async def test_current_conditions(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api) -> None:
    await setup_entry(hass, config_entry)

    state = hass.states.get(ENTITY_ID)
    assert state.state == "cloudy"  # icon "ovc"
    assert state.attributes["temperature"] == 13.1
    assert state.attributes["apparent_temperature"] == 14.2
    assert state.attributes["dew_point"] == 7.3
    assert state.attributes["humidity"] == 68
    assert state.attributes["pressure"] == 1021.8
    assert state.attributes["wind_bearing"] == 68
    assert state.attributes["wind_speed"] == 0
    # `gust_max` is the day's peak, not the current gust — deliberately absent.
    assert "wind_gust_speed" not in state.attributes


async def test_daily_forecast(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    await setup_entry(hass, config_entry)

    forecast = await _forecast(hass, "daily")

    assert len(forecast) == 8
    assert [day["datetime"][:10] for day in forecast] == [
        "2026-09-24", "2026-09-25", "2026-09-26", "2026-09-27",
        "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01",
    ]
    assert forecast[0] == {
        "datetime": "2026-09-24T00:00:00+02:00",
        "condition": "cloudy",
        "temperature": 19,
        "templow": 10,
        "precipitation_probability": 0,
        "precipitation": 0,
        "wind_speed": 10,
        "wind_gust_speed": 29,
        "wind_bearing": 325,
    }
    assert forecast[7]["precipitation"] == 3.8


async def test_daily_forecast_counts_days_in_berlin(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, api_response
) -> None:
    """Shortly after midnight in Berlin an instance in another zone is still on yesterday."""
    await hass.config.async_set_time_zone("America/Los_Angeles")
    api_response["meta"]["generated"] = "2026-09-25T00:30:00+02:00"  # 24.09., 15:30 in Los Angeles
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    forecast = await _forecast(hass, "daily")

    assert forecast[0]["datetime"] == "2026-09-25T00:00:00-07:00"


async def test_hourly_forecast(hass: HomeAssistant, config_entry: MockConfigEntry, mock_api) -> None:
    await setup_entry(hass, config_entry)

    forecast = await _forecast(hass, "hourly")

    assert len(forecast) == 12
    times = [datetime.fromisoformat(hour["datetime"]) for hour in forecast]
    assert times[0] == datetime.fromisoformat("2026-09-24T07:00:00+02:00")
    assert times[-1] == datetime.fromisoformat("2026-09-24T18:00:00+02:00")
    assert forecast[4] == {
        "datetime": forecast[4]["datetime"],
        "condition": "cloudy",
        "temperature": 15,
        "precipitation_probability": 3,
        "wind_speed": 7,
    }
    assert [hour["condition"] for hour in forecast[-2:]] == ["partlycloudy", "sunny"]


async def test_forecast_follows_new_data(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, api_response
) -> None:
    """The caches are dropped on every coordinator update."""
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)
    assert (await _forecast(hass, "daily"))[0]["temperature"] == 19
    assert (await _forecast(hass, "hourly"))[0]["temperature"] == 13

    api_response["days"][0]["tmax"] = 21
    api_response["hours"][0]["temp"] = 14
    respond_with(aioclient_mock, json=api_response)
    await _refresh(hass, config_entry)

    assert (await _forecast(hass, "daily"))[0]["temperature"] == 21
    assert (await _forecast(hass, "hourly"))[0]["temperature"] == 14


async def test_subscribers_get_new_forecast(
    hass: HomeAssistant, hass_ws_client, config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker, api_response
) -> None:
    """An open dashboard is pushed the new forecast, not left on the old one."""
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {"type": "weather/subscribe_forecast", "forecast_type": "daily", "entity_id": ENTITY_ID}
    )
    assert (await client.receive_json())["success"]
    first = await client.receive_json()
    assert first["event"]["forecast"][0]["temperature"] == 19

    api_response["days"][0]["tmax"] = 21
    respond_with(aioclient_mock, json=api_response)
    await _refresh(hass, config_entry)

    # Bounded: without the push this would wait forever instead of failing.
    async with asyncio.timeout(5):
        pushed = await client.receive_json()
    assert pushed["event"]["forecast"][0]["temperature"] == 21


async def test_no_forecast_data(
    hass: HomeAssistant, config_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, api_response
) -> None:
    del api_response["days"]
    api_response["hours"] = []
    respond_with(aioclient_mock, json=api_response)
    await setup_entry(hass, config_entry)

    assert await _forecast(hass, "daily") == []
    assert await _forecast(hass, "hourly") == []


# --- icon table --------------------------------------------------------------------

_VALID_CONDITIONS = {
    value for name, value in vars(weather).items() if name.startswith("ATTR_CONDITION_")
}


def test_icon_map_covers_all_documented_codes() -> None:
    """19 codes, confirmed against the API docs — do not re-derive from icons."""
    assert len(kw_weather.ICON_MAP) == 19
    assert set(kw_weather.ICON_MAP.values()) <= _VALID_CONDITIONS


def test_all_storm_codes_carry_rain() -> None:
    """`storm` is the weak thunderstorm *with* rain, not a dry one (AGENTS.md)."""
    for code in ("storm", "sunstorm", "storm-rain", "storm-svr"):
        assert kw_weather.ICON_MAP[code] == "lightning-rainy"


def test_unknown_icon_warns_once(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(kw_weather, "_warned_icons", set())

    assert kw_weather._condition("hail-new") is None
    assert kw_weather._condition("hail-new") is None
    assert kw_weather._condition(None) is None

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
