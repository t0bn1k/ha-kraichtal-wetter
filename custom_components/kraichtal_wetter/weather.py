from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_API_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The API states its times in Europe/Berlin, whatever the Home Assistant
# instance is set to (see docs/API.md), so the hourly labels are read in that
# zone rather than the local one.
API_TIME_ZONE = dt_util.get_time_zone("Europe/Berlin")

_HOUR = timedelta(hours=1)

# Maps the API's icon names onto Home Assistant weather conditions. Only the
# values in homeassistant.components.weather.ATTR_CONDITION_* are valid; an
# unknown icon deliberately yields None ("unknown") rather than a wrong guess.
#
# This table is authoritative: the API author confirmed it against the function
# that emits the codes, not against the dashboard's SVG registry we previously
# reverse-engineered. Do not "correct" an entry from what its icon draws — that
# is what produced the wrong sunstorm/storm mapping this replaces.
#
# All four storm codes carry rain. `storm` is the *weakest* thunderstorm, not
# the dry one; `storm-rain` is simply the normal case. A thunderstorm without
# precipitation has no code at all, so ATTR_CONDITION_LIGHTNING is unreachable
# from this source and deliberately absent below.
#
# Day/night variants exist only for clear and light cloud (sun/moon,
# suncloud/mooncloud); rain, snow, storm and fog use one code around the clock.
# `mooncloud` is the broader of its pair — an overcast night arrives as
# `mooncloud` too, since there is no night counterpart to `ovc`, so
# partlycloudy occasionally understates it. There is no better option.
#
# Unreachable for the same reason (no code exists): `hail` and `windy` live in
# the alert and wind fields rather than in `icon`, sleet/freezing rain is
# folded into `snow`, and nothing maps to `exceptional`.
ICON_MAP = {
    "sun": "sunny",
    "moon": "clear-night",
    "suncloud": "partlycloudy",
    "mooncloud": "partlycloudy",
    "cloud": "cloudy",
    "ovc": "cloudy",
    "fog": "fog",
    "drizzle": "rainy",
    "rain": "rainy",
    "sunrain": "rainy",
    "rain-hvy": "pouring",
    "storm": "lightning-rainy",
    "sunstorm": "lightning-rainy",
    "storm-rain": "lightning-rainy",
    "storm-svr": "lightning-rainy",
    "snow-lgt": "snowy",
    "snow": "snowy",
    "snow-hvy": "snowy",
    "sunsnow": "snowy",
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


def _label_hour(label: object) -> int | None:
    """Return the full hour an hourly label names.

    None for the first entry's "Jetzt" and for anything unexpected — those
    entries simply follow the hour before them.
    """
    if not isinstance(label, str):
        return None
    hour, _, minute = label.partition(":")
    if minute != "00" or not hour.isdigit() or not 0 <= int(hour) <= 23:
        return None
    return int(hour)


def _hourly_datetimes(generated: datetime, labels: list[object]) -> list[datetime]:
    """Turn the hourly labels into timestamps.

    The API dates its hourly entries only by label ("Jetzt", "15:00"), so the
    times have to be reconstructed. Two rules keep that honest:

    - The series is anchored on the first labelled entry — the API's own
      statement of a time — and `meta.generated` only decides which day that
      label belongs to. Anchoring on `generated` instead would be a guess about
      whether the API rounds "Jetzt" up or down.
    - From there we step in UTC, so an hour stays an hour when the clocks
      change: the repeated 02:00 in October becomes two distinct instants that
      both match their label. Where a label disagrees with the step — a gap in
      the series — we follow the label and carry on from there.
    """
    base = generated.astimezone(API_TIME_ZONE).replace(minute=0, second=0, microsecond=0)

    anchor_index, anchor = 0, base
    for index, label in enumerate(labels):
        if (hour := _label_hour(label)) is None:
            continue
        anchor_index, anchor = index, base.replace(hour=hour)
        if anchor < base:
            # The label is already past midnight, so it belongs to the next day.
            anchor += timedelta(days=1)
        break

    times = [anchor] * len(labels)
    for index in range(anchor_index - 1, -1, -1):  # "Jetzt" and anything before
        times[index] = (dt_util.as_utc(times[index + 1]) - _HOUR).astimezone(API_TIME_ZONE)
    for index in range(anchor_index + 1, len(labels)):
        previous = times[index - 1]
        moment = (dt_util.as_utc(previous) + _HOUR).astimezone(API_TIME_ZONE)
        hour = _label_hour(labels[index])
        if hour is not None and moment.hour != hour:
            moment = previous.replace(hour=hour)
            while moment <= previous:
                moment += timedelta(days=1)
        times[index] = moment
    return times


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
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "kraichtal_wetter_forecast"
        self._forecast_cache: list[Forecast] | None = None
        self._hourly_cache: list[Forecast] | None = None
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
    def native_apparent_temperature(self) -> float | None:
        return self._current().get("feels_like")

    @property
    def native_dew_point(self) -> float | None:
        return self._current().get("dewpoint")

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

    # Deliberately no native_wind_gust_speed for the current conditions:
    # `gust_max` is the strongest gust of the day so far, not the current one,
    # and the API has no field for the latter.

    def _generated(self) -> datetime:
        """Return the time the API generated this response."""
        data = self.coordinator.data
        meta = data.get("meta") if isinstance(data, dict) else None
        generated = meta.get("generated") if isinstance(meta, dict) else None

        parsed = dt_util.parse_datetime(generated) if isinstance(generated, str) else None
        return parsed if parsed is not None else dt_util.utcnow()

    def _base_day(self) -> date:
        """Return the day the forecast starts on, as the API counts days.

        Read in the API's own zone: shortly after midnight in Berlin, an
        instance set to another time zone is still on the previous date and
        would shift the whole forecast by a day.
        """
        return self._generated().astimezone(API_TIME_ZONE).date()

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

            # Local midnight, so the card labels each entry with the weekday the
            # viewer expects; re-derived per day so DST transitions stay correct.
            day_start = dt_util.start_of_local_day(base_day + timedelta(days=idx))

            forecast.append(
                {
                    "datetime": day_start.isoformat(),
                    "condition": _condition(day.get("icon")),
                    "native_temperature": day.get("tmax"),
                    "native_templow": day.get("tmin"),
                    "precipitation_probability": day.get("pop"),
                    "native_precipitation": day.get("rain"),
                    "native_wind_speed": day.get("wind"),
                    # Expected peak gust; HA converts it with the wind speed unit.
                    "native_wind_gust_speed": day.get("gust"),
                    # null when the day is forecast windstill, per the API docs.
                    "wind_bearing": day.get("wind_dir"),
                }
            )
        return forecast or None

    def _build_hourly_forecast(self) -> list[Forecast] | None:
        data = self.coordinator.data
        if not isinstance(data, dict):
            return None

        hours = data.get("hours")
        if not isinstance(hours, list):
            return None

        entries = [hour for hour in hours if isinstance(hour, dict)]
        times = _hourly_datetimes(self._generated(), [entry.get("label") for entry in entries])

        forecast: list[Forecast] = [
            {
                "datetime": moment.isoformat(),
                "condition": _condition(entry.get("icon")),
                "native_temperature": entry.get("temp"),
                "precipitation_probability": entry.get("pop"),
                "native_wind_speed": entry.get("wind"),
                # The hourly entries carry no rain amount and no wind direction.
            }
            for entry, moment in zip(entries, times)
        ]
        return forecast or None

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        if self._forecast_cache is None:
            self._forecast_cache = self._build_forecast()
        return self._forecast_cache

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the next twelve hours in native units."""
        if self._hourly_cache is None:
            self._hourly_cache = self._build_hourly_forecast()
        return self._hourly_cache

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._forecast_cache = None
        self._hourly_cache = None
        super()._handle_coordinator_update()
        # Writing the state does not reach a card that subscribed to the
        # forecast — those listeners have to be pushed to explicitly, which is
        # what HA's own CoordinatorWeatherEntity does on every update. Without
        # this the forecast in an open dashboard stays on the data it was
        # opened with.
        if entry := self.coordinator.config_entry:
            entry.async_create_task(self.hass, self.async_update_listeners(None))
