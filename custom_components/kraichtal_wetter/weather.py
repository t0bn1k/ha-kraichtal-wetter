from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import UnitOfPressure, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_API_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Maps the API's icon names onto Home Assistant weather conditions. Only the
# values in homeassistant.components.weather.ATTR_CONDITION_* are valid; an
# unknown icon deliberately yields None ("unknown") rather than a wrong guess.
#
# The full set of codes below was confirmed against the icon registry the
# public dashboard (kraichtal-wetter.de/dashboard/) embeds for rendering
# forecast/hourly icons (`const I = {...}` in its inline <script>) — that
# object is the complete vocabulary the API can emit, not just what we've
# happened to observe so far.
ICON_MAP = {
    "sun": "sunny",
    "moon": "clear-night",
    "suncloud": "partlycloudy",
    "mooncloud": "partlycloudy",
    "cloud": "cloudy",
    "ovc": "cloudy",
    "drizzle": "rainy",
    "rain": "rainy",
    "sunrain": "rainy",
    "rain-hvy": "pouring",
    "storm": "lightning",
    "sunstorm": "lightning-rainy",
    "storm-rain": "pouring",
    "storm-svr": "lightning-rainy",
    "snow-lgt": "snowy",
    "snow": "snowy",
    "snow-hvy": "snowy",
    "sunsnow": "snowy-rainy",
}

# Icons we've already warned about, so a persistently unmapped icon (e.g. one
# sent every poll overnight) logs once instead of spamming at scan_interval.
_warned_icons: set[object] = set()


def _condition(icon: object) -> str | None:
    """Translate an API icon name into a HA weather condition."""
    if icon is None:
        return None
    condition = ICON_MAP.get(icon)
    if condition is None:
        if icon in _warned_icons:
            _LOGGER.debug("Unmapped Kraichtal Wetter icon: %r", icon)
        else:
            _warned_icons.add(icon)
            _LOGGER.warning(
                "Unmapped Kraichtal Wetter icon: %r - condition will show as "
                "unknown until ICON_MAP is extended for it",
                icon,
            )
    return condition


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([KraichtalWetterWeather(coordinator, entry)], True)


class KraichtalWetterWeather(CoordinatorEntity, WeatherEntity):
    # name = None marks this as the device's primary entity: it takes the
    # device name ("Kraichtal Wetter") for both display and entity_id.
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "kraichtal_wetter_forecast"
        self._forecast_cache: list[Forecast] | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Kraichtal Wetter",
            manufacturer="Kraichtal Wetter",
            model="Kraichtal Wetter Station",
            configuration_url=entry.data.get(CONF_API_URL, ""),
        )

    def _current(self) -> dict:
        data = self.coordinator.data
        if not isinstance(data, dict):
            return {}
        current = data.get("current")
        return current if isinstance(current, dict) else {}

    @property
    def native_temperature(self) -> float | None:
        return self._current().get("temp")

    @property
    def humidity(self) -> float | None:
        return self._current().get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self._current().get("pressure")

    @property
    def condition(self) -> str | None:
        return _condition(self._current().get("icon"))

    @property
    def wind_bearing(self) -> float | None:
        return self._current().get("wind_dir")

    @property
    def native_wind_speed(self) -> float | None:
        return self._current().get("wind")

    def _base_day(self) -> datetime:
        """Return local midnight of the day the forecast was generated."""
        data = self.coordinator.data
        meta = data.get("meta") if isinstance(data, dict) else None
        generated = meta.get("generated") if isinstance(meta, dict) else None

        parsed = dt_util.parse_datetime(generated) if isinstance(generated, str) else None
        if parsed is None:
            parsed = dt_util.utcnow()

        return dt_util.start_of_local_day(dt_util.as_local(parsed))

    def _build_forecast(self) -> list[Forecast] | None:
        data = self.coordinator.data
        if not isinstance(data, dict):
            return None

        days = data.get("days")
        if not isinstance(days, list):
            return None

        base_day = self._base_day()

        forecast: list[Forecast] = []
        for idx, day in enumerate(days):
            if not isinstance(day, dict):
                continue

            # Re-derive local midnight per day so DST transitions stay correct.
            day_start = dt_util.start_of_local_day(base_day.date() + timedelta(days=idx))

            forecast.append(
                {
                    "datetime": day_start.isoformat(),
                    "condition": _condition(day.get("icon")),
                    "native_temperature": day.get("tmax"),
                    "native_templow": day.get("tmin"),
                    "precipitation_probability": day.get("pop"),
                    "native_wind_speed": day.get("wind"),
                    "wind_bearing": day.get("wind_dir"),
                }
            )
        return forecast or None

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        if self._forecast_cache is None:
            self._forecast_cache = self._build_forecast()
        return self._forecast_cache

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._forecast_cache = None
        super()._handle_coordinator_update()
