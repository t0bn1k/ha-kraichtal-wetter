import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import KraichtalWetterClient

_LOGGER = logging.getLogger(__name__)

# Before 0.5.0 the sensors carried hardcoded German names, from which Home
# Assistant derived entity ids like sensor.kraichtal_wetter_boen_max. 0.5.0
# moved the names into translations/, so the ids are now derived from the
# English names instead. Rename the existing registry entries rather than
# leaving them behind, which would orphan their recorder history.
#
# Maps the sensor `key` to (old object id, new object id).
_SENSOR_ENTITY_ID_MIGRATION: dict[str, tuple[str, str]] = {
    "temp": ("kraichtal_wetter_aussentemperatur", "kraichtal_wetter_outdoor_temperature"),
    "feels_like": ("kraichtal_wetter_gefuhlt", "kraichtal_wetter_feels_like"),
    "dewpoint": ("kraichtal_wetter_taupunkt", "kraichtal_wetter_dew_point"),
    "humidity": ("kraichtal_wetter_luftfeuchtigkeit", "kraichtal_wetter_humidity"),
    "pressure": ("kraichtal_wetter_luftdruck", "kraichtal_wetter_pressure"),
    "wind": ("kraichtal_wetter_windgeschwindigkeit", "kraichtal_wetter_wind_speed"),
    "wind_dir": ("kraichtal_wetter_windrichtung", "kraichtal_wetter_wind_direction"),
    "gust_max": ("kraichtal_wetter_boen_max", "kraichtal_wetter_max_gust"),
    "solar": ("kraichtal_wetter_solarstrahlung", "kraichtal_wetter_solar_irradiance"),
    "rain": ("kraichtal_wetter_niederschlag_aktuell", "kraichtal_wetter_precipitation"),
    "tmax_today": (
        "kraichtal_wetter_maximale_temperatur_heute",
        "kraichtal_wetter_max_temperature_today",
    ),
    "tmin_today": (
        "kraichtal_wetter_minimale_temperatur_heute",
        "kraichtal_wetter_min_temperature_today",
    ),
    "rain_today": (
        "kraichtal_wetter_niederschlag_heute",
        "kraichtal_wetter_precipitation_today",
    ),
    "warnings": ("kraichtal_wetter_warnungen", "kraichtal_wetter_warnings"),
    "obs_date": ("kraichtal_wetter_beobachtungsdatum", "kraichtal_wetter_observation_date"),
    "obs_time": ("kraichtal_wetter_beobachtungszeit", "kraichtal_wetter_observation_time"),
    "realtime": ("kraichtal_wetter_echtzeitdaten", "kraichtal_wetter_realtime_data"),
    "station_today.tmax": (
        "kraichtal_wetter_station_heute_tmax",
        "kraichtal_wetter_station_max_temperature_today",
    ),
    "station_today.tmin": (
        "kraichtal_wetter_station_heute_tmin",
        "kraichtal_wetter_station_min_temperature_today",
    ),
    "station_today.gust": (
        "kraichtal_wetter_station_heute_boe",
        "kraichtal_wetter_station_max_gust_today",
    ),
    "station_today.press_max": (
        "kraichtal_wetter_station_heute_luftdruck_max",
        "kraichtal_wetter_station_max_pressure_today",
    ),
    "station_today.press_min": (
        "kraichtal_wetter_station_heute_luftdruck_min",
        "kraichtal_wetter_station_min_pressure_today",
    ),
}

# The weather entity became the device's primary entity in 0.5.0, so it now
# takes the plain device name instead of a "Forecast" suffix.
# (unique_id, old object id, new object id)
_WEATHER_ENTITY_ID_MIGRATION = (
    "kraichtal_wetter_forecast",
    "kraichtal_wetter_forecast",
    "kraichtal_wetter",
)


@callback
def _async_migrate_entity_ids(hass: HomeAssistant) -> None:
    """Rename the pre-0.5.0 German-derived entity ids."""
    registry = er.async_get(hass)

    migrations = [
        ("sensor", f"kraichtal_wetter_{key}", old_object_id, new_object_id)
        for key, (old_object_id, new_object_id) in _SENSOR_ENTITY_ID_MIGRATION.items()
    ]
    migrations.append(("weather", *_WEATHER_ENTITY_ID_MIGRATION))

    for platform, unique_id, old_object_id, new_object_id in migrations:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id is None:
            continue

        # Only touch entities still carrying the old generated id, so an id the
        # user picked themselves is never overwritten.
        if entity_id != f"{platform}.{old_object_id}":
            continue

        new_entity_id = f"{platform}.{new_object_id}"
        if registry.async_get(new_entity_id) is not None:
            _LOGGER.warning(
                "Not renaming %s: %s already exists", entity_id, new_entity_id
            )
            continue

        _LOGGER.info("Migrating entity id %s to %s", entity_id, new_entity_id)
        registry.async_update_entity(entity_id, new_entity_id=new_entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api_url = entry.data.get(CONF_API_URL, DEFAULT_API_URL)
    # Backwards compatibility: older installs may have stored the API key as
    # 'api_key' or 'apikey'. Prefer the configured `CONF_API_KEY` (now 'key').
    api_key = entry.data.get(CONF_API_KEY) or entry.data.get("api_key") or entry.data.get("apikey")
    # The flows reject anything below MIN_SCAN_INTERVAL, but an entry
    # configured before that was enforced still carries its old value — the
    # schema never sees it again. Lift it here so no install keeps polling
    # faster than the API's five-minute cache can answer.
    stored_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = max(stored_interval, MIN_SCAN_INTERVAL)
    if scan_interval != stored_interval:
        _LOGGER.warning(
            "Configured scan interval of %s s is below the %s s minimum "
            "(the API caches for five minutes); using %s s instead",
            stored_interval,
            MIN_SCAN_INTERVAL,
            scan_interval,
        )

    session = async_get_clientsession(hass)
    client = KraichtalWetterClient(api_url, api_key, session)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        config_entry=entry,
        name="Kraichtal Wetter",
        update_method=client.async_update,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Raises ConfigEntryNotReady on a transient failure (HA retries the setup)
    # and lets ConfigEntryAuthFailed through so HA can start the reauth flow.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "entry": entry,
    }

    # Must run before the platforms are set up so the entities attach to the
    # renamed registry entries instead of claiming the old ids again.
    _async_migrate_entity_ids(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
