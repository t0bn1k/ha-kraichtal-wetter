from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import KraichtalWetterConfigEntry
from .entity import device_info

# Every entity reads the coordinator's data; none polls on its own.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class KraichtalWetterSensorEntityDescription(SensorEntityDescription):
    """Sensor description that can surface further API fields as attributes."""

    # API section that `key` and the attribute fields are looked up in. Numeric
    # parts index into arrays, so `days` + "1.tmin" is days[1]["tmin"]. Sensors
    # outside `current` carry the section in their unique_id; those in
    # `current` keep the bare key they have always had.
    section: str = "current"
    # (attribute name, API field) pairs; the field uses the same dot notation
    # as `key`. Attribute names are translated under
    # entity.sensor.<translation_key>.state_attributes. A tuple rather than a
    # dict keeps the frozen description hashable.
    attributes: tuple[tuple[str, str], ...] = ()


# `key` addresses the API payload within `section` (dot notation for nested
# fields) and forms the unique_id; `translation_key` selects the display name
# from translations/.
#
# NOTE: Home Assistant builds the entity_id from the name in the instance's
# own language (German is one of the languages it does that for), prefixed with
# the area and device. So both translation files move entity_ids for new
# installs, not just en.json — see AGENTS.md and _SENSOR_ENTITY_ID_MIGRATION in
# __init__.py.
SENSOR_TYPES = [
    KraichtalWetterSensorEntityDescription(
        # When the station has no reading, the API fills `temp` from the
        # forecast and says so in `temp_source` (live / forecast). The value
        # enters the statistics either way; the attribute at least makes a
        # stand-in visible instead of letting it pass for a measurement.
        key="temp",
        translation_key="temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        attributes=(("source", "temp_source"),),
    ),
    KraichtalWetterSensorEntityDescription(
        key="feels_like",
        translation_key="feels_like",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-lines",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="dewpoint",
        translation_key="dewpoint",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:water-percent",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="wind",
        translation_key="wind",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        # The circular-averaging problem that previously kept this sensor
        # without a state class is what MEASUREMENT_ANGLE solves: the recorder
        # computes a circular mean, so a wind oscillating either side of north
        # no longer averages to south. Home Assistant enforces this pairing —
        # WIND_DIRECTION accepts no other state class, and no unit but DEGREE.
        key="wind_dir",
        translation_key="wind_dir",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass",
        device_class=SensorDeviceClass.WIND_DIRECTION,
        state_class=SensorStateClass.MEASUREMENT_ANGLE,
    ),
    KraichtalWetterSensorEntityDescription(
        key="gust_max",
        translation_key="gust_max",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="solar",
        translation_key="solar",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        icon="mdi:weather-sunny",
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        # Precipitation measured by the station's rain gauge since midnight
        # (API docs: "Niederschlag heute (Station)"). It climbs in 0.2 mm steps
        # and drops to 0 at midnight — the case the HA docs name for
        # TOTAL_INCREASING ("a daily amount of consumed gas"). TOTAL without
        # last_reset, which the docs prefer wherever it works, does not work
        # here: with no reset marker the recorder just sums deltas, so the drop
        # to 0 at midnight would subtract the day's rain from the long-term
        # total instead of starting a new cycle.
        #
        # Not to be confused with `rain_today` below, which despite its name is
        # a forecast. Before 0.7.0 the two were treated the other way round.
        key="rain",
        translation_key="rain",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # tmax_today, tmin_today and rain_today are forecasts, not measurements.
    # The API derives them from the hourly forecast for the hours still left
    # today (past hours are null in its `today` section), so they shrink
    # towards the evening: at 23:00, tmax_today is little more than the next
    # hour's temperature, not the day's high. The measured counterparts are
    # station_today.* and `rain`; the full-day forecast is days[0].
    #
    # Hence no state class. The HA docs exclude "a prediction of the future"
    # from MEASUREMENT by name, and TOTAL_INCREASING on rain_today turned every
    # downward revision of the forecast into a meter reset, inflating the
    # long-term sum (5 Sep 2026: 9.5 mm recorded, 3.4 mm actually fell).
    KraichtalWetterSensorEntityDescription(
        key="tmax_today",
        translation_key="tmax_today",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    KraichtalWetterSensorEntityDescription(
        key="tmin_today",
        translation_key="tmin_today",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-low",
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    KraichtalWetterSensorEntityDescription(
        key="rain_today",
        translation_key="rain_today",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
    ),
    # The daily forecast (days, index 0 = today) as single states, so an
    # automation can ask "frost tomorrow?" without weather.get_forecasts and a
    # template. Unlike the *_today sensors above, a day covers the whole
    # calendar day: tmin of days[1] includes the night after midnight, which
    # is what a frost check needs. Forecasts again, so no state class.
    #
    # `confidence` is how far the weather models agree on that day (API docs:
    # "Wie einig sich die Wettermodelle sind", in %). The weather entity's
    # forecast has no field for it, hence the attribute.
    KraichtalWetterSensorEntityDescription(
        section="days",
        key="0.pop",
        translation_key="pop_today",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:umbrella-outline",
        attributes=(("confidence", "0.confidence"),),
    ),
    KraichtalWetterSensorEntityDescription(
        section="days",
        key="1.tmax",
        translation_key="tmax_tomorrow",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        device_class=SensorDeviceClass.TEMPERATURE,
        attributes=(("confidence", "1.confidence"),),
    ),
    KraichtalWetterSensorEntityDescription(
        section="days",
        key="1.tmin",
        translation_key="tmin_tomorrow",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-low",
        device_class=SensorDeviceClass.TEMPERATURE,
        attributes=(("confidence", "1.confidence"),),
    ),
    KraichtalWetterSensorEntityDescription(
        section="days",
        key="1.rain",
        translation_key="rain_tomorrow",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        icon="mdi:weather-rainy",
        device_class=SensorDeviceClass.PRECIPITATION,
        attributes=(("confidence", "1.confidence"),),
    ),
    KraichtalWetterSensorEntityDescription(
        section="days",
        key="1.pop",
        translation_key="pop_tomorrow",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:umbrella-outline",
        attributes=(("confidence", "1.confidence"),),
    ),
    KraichtalWetterSensorEntityDescription(
        key="warnings",
        translation_key="warnings",
        icon="mdi:alarm",
    ),
    KraichtalWetterSensorEntityDescription(
        key="obs_date",
        translation_key="obs_date",
        icon="mdi:calendar",
    ),
    KraichtalWetterSensorEntityDescription(
        key="obs_time",
        translation_key="obs_time",
        icon="mdi:clock",
    ),
    KraichtalWetterSensorEntityDescription(
        key="realtime",
        translation_key="realtime",
        icon="mdi:clock-fast",
    ),
    KraichtalWetterSensorEntityDescription(
        # The `*_time` fields arrive as "HH:MM" local time and are passed
        # through as-is: turning them into datetimes would mean pairing them
        # with a date, and around midnight it is unclear which one.
        key="station_today.tmax",
        translation_key="station_today_tmax",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-high",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        attributes=(("time", "station_today.tmax_time"),),
    ),
    KraichtalWetterSensorEntityDescription(
        key="station_today.tmin",
        translation_key="station_today_tmin",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-low",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        attributes=(("time", "station_today.tmin_time"),),
    ),
    KraichtalWetterSensorEntityDescription(
        key="station_today.gust",
        translation_key="station_today_gust",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        attributes=(
            ("time", "station_today.gust_time"),
            ("beaufort", "station_today.gust_bft"),
        ),
    ),
    KraichtalWetterSensorEntityDescription(
        key="station_today.wind_max",
        translation_key="station_today_wind_max",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        icon="mdi:weather-windy",
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="station_today.press_max",
        translation_key="station_today_press_max",
        native_unit_of_measurement=UnitOfPressure.HPA,
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    KraichtalWetterSensorEntityDescription(
        key="station_today.press_min",
        translation_key="station_today_press_min",
        native_unit_of_measurement=UnitOfPressure.HPA,
        icon="mdi:gauge",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]


async def async_setup_entry(hass, entry: KraichtalWetterConfigEntry, async_add_entities):
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        KraichtalWetterSensor(coordinator, entry, description) for description in SENSOR_TYPES
    ]
    entities.append(KraichtalWetterApiStatusSensor(coordinator, entry))
    async_add_entities(entities, True)


def _resolve_value(data: object, section: str, key: str):
    if not isinstance(data, dict):
        return None

    value: object = data.get(section)
    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value


def unique_id(description: KraichtalWetterSensorEntityDescription) -> str:
    if description.section == "current":
        return f"kraichtal_wetter_{description.key}"
    return f"kraichtal_wetter_{description.section}.{description.key}"


class KraichtalWetterSensor(CoordinatorEntity, SensorEntity):
    entity_description: KraichtalWetterSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator, entry, description: KraichtalWetterSensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = unique_id(description)
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self):
        description = self.entity_description
        return _resolve_value(self.coordinator.data, description.section, description.key)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        section = self.entity_description.section
        attributes = {
            name: value
            for name, api_field in self.entity_description.attributes
            if (value := _resolve_value(self.coordinator.data, section, api_field)) is not None
        }
        return attributes or None


class KraichtalWetterApiStatusSensor(CoordinatorEntity, SensorEntity):
    """Surfaces the last API failure on the device page.

    Everything else in this integration goes unavailable when an update fails,
    which is precisely when the reason matters — so this entity deliberately
    stays available and reports what went wrong instead.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:api"
    _attr_translation_key = "api_status"

    # A sensor state longer than this is rejected by the state machine, and the
    # API's message is free text — so the state is truncated and the full text
    # kept as an attribute.
    _MAX_STATE_LENGTH = 255

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "kraichtal_wetter_api_status"
        self._attr_device_info = device_info(entry)

    @property
    def available(self) -> bool:
        """Always available — reporting the outage is this entity's job."""
        return True

    def _error(self) -> str | None:
        if self.coordinator.last_update_success:
            return None
        error = self.coordinator.last_exception
        return str(error) if error else "unknown error"

    @property
    def native_value(self) -> str:
        error = self._error()
        if error is None:
            return "ok"
        return error[: self._MAX_STATE_LENGTH]

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        error = self._error()
        return {"last_error": error} if error else None
