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

# Entity ids earlier versions left behind, per sensor `key`. 0.5.0 renamed
# every entity to its *English* name, assuming ids were language-independent;
# they are not — Home Assistant derives them from the name in the language of
# the instance. Before 0.5.0 the ids came from the hardcoded German names, so
# both sets are listed: an install may have skipped 0.5.0 entirely.
#
# Only an entity still carrying one of these is renamed, so an id the user
# picked themselves is never touched. There is no target id here on purpose —
# it is asked of Home Assistant, see _async_migrate_entity_ids().
_LEGACY_SENSOR_OBJECT_IDS: dict[str, tuple[str, ...]] = {
    "temp": ("kraichtal_wetter_outdoor_temperature", "kraichtal_wetter_aussentemperatur"),
    "feels_like": ("kraichtal_wetter_feels_like", "kraichtal_wetter_gefuhlt"),
    "dewpoint": ("kraichtal_wetter_dew_point", "kraichtal_wetter_taupunkt"),
    "humidity": ("kraichtal_wetter_humidity", "kraichtal_wetter_luftfeuchtigkeit"),
    "pressure": ("kraichtal_wetter_pressure", "kraichtal_wetter_luftdruck"),
    "wind": ("kraichtal_wetter_wind_speed", "kraichtal_wetter_windgeschwindigkeit"),
    "wind_dir": ("kraichtal_wetter_wind_direction", "kraichtal_wetter_windrichtung"),
    "gust_max": ("kraichtal_wetter_max_gust", "kraichtal_wetter_boen_max"),
    "solar": ("kraichtal_wetter_solar_irradiance", "kraichtal_wetter_solarstrahlung"),
    "rain": ("kraichtal_wetter_precipitation", "kraichtal_wetter_niederschlag_aktuell"),
    "tmax_today": (
        "kraichtal_wetter_max_temperature_today",
        "kraichtal_wetter_maximale_temperatur_heute",
    ),
    "tmin_today": (
        "kraichtal_wetter_min_temperature_today",
        "kraichtal_wetter_minimale_temperatur_heute",
    ),
    "rain_today": (
        "kraichtal_wetter_precipitation_today",
        "kraichtal_wetter_niederschlag_heute",
    ),
    "warnings": ("kraichtal_wetter_warnings", "kraichtal_wetter_warnungen"),
    "obs_date": (
        "kraichtal_wetter_observation_date",
        "kraichtal_wetter_beobachtungsdatum",
    ),
    "obs_time": (
        "kraichtal_wetter_observation_time",
        "kraichtal_wetter_beobachtungszeit",
    ),
    "realtime": ("kraichtal_wetter_realtime_data", "kraichtal_wetter_echtzeitdaten"),
    "station_today.tmax": (
        "kraichtal_wetter_station_max_temperature_today",
        "kraichtal_wetter_station_heute_tmax",
    ),
    "station_today.tmin": (
        "kraichtal_wetter_station_min_temperature_today",
        "kraichtal_wetter_station_heute_tmin",
    ),
    "station_today.gust": (
        "kraichtal_wetter_station_max_gust_today",
        "kraichtal_wetter_station_heute_boe",
    ),
    "station_today.press_max": (
        "kraichtal_wetter_station_max_pressure_today",
        "kraichtal_wetter_station_heute_luftdruck_max",
    ),
    "station_today.press_min": (
        "kraichtal_wetter_station_min_pressure_today",
        "kraichtal_wetter_station_heute_luftdruck_min",
    ),
}

# The weather entity became the device's primary entity in 0.5.0 and dropped
# the "Forecast" suffix; its name is the device name in every language.
_LEGACY_WEATHER_OBJECT_IDS = ("kraichtal_wetter_forecast", "kraichtal_wetter")

# Entry ids whose entities still need the rename below, remembered between
# async_migrate_entry (which runs before the platforms) and async_setup_entry.
_PENDING_ID_MIGRATION = f"{DOMAIN}_pending_entity_id_migration"


@callback
def _async_migrate_entity_ids(hass: HomeAssistant) -> None:
    """Regenerate entity ids that earlier versions left in the wrong shape.

    The new id is not spelled out here — `async_regenerate_entity_id()` builds
    the one Home Assistant would give the entity today: in the language of the
    instance and in the format configured for entity ids, which since 2026.8
    the user chooses (area, floor, device, entity). Whatever they picked, the
    migrated entities end up looking like freshly created ones.
    """
    registry = er.async_get(hass)

    candidates = [
        ("sensor", f"kraichtal_wetter_{key}", object_ids)
        for key, object_ids in _LEGACY_SENSOR_OBJECT_IDS.items()
    ]
    candidates.append(
        ("weather", "kraichtal_wetter_forecast", _LEGACY_WEATHER_OBJECT_IDS)
    )

    for platform, unique_id, legacy_object_ids in candidates:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id is None:
            continue

        if entity_id not in {f"{platform}.{object_id}" for object_id in legacy_object_ids}:
            continue

        entry = registry.async_get(entity_id)
        if entry is None:
            continue

        new_entity_id = registry.async_regenerate_entity_id(entry)
        if new_entity_id == entity_id:
            continue

        _LOGGER.info("Migrating entity id %s to %s", entity_id, new_entity_id)
        registry.async_update_entity(entity_id, new_entity_id=new_entity_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an older config entry.

    Home Assistant calls this before the entry is set up and only while the
    stored version differs, which is what makes the rename a one-off: a fresh
    install starts at the current version and is never touched. The rename
    itself waits for async_setup_entry, because the registry only carries the
    current entity names once the platforms have registered their entities.
    """
    if entry.version < 2:
        hass.data.setdefault(_PENDING_ID_MIGRATION, set()).add(entry.entry_id)
        hass.config_entries.async_update_entry(entry, version=2)

    return True


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Only now does the registry know the entities' current names, which is
    # what the regenerated ids are built from (see async_migrate_entry).
    if entry.entry_id in hass.data.get(_PENDING_ID_MIGRATION, ()):
        hass.data[_PENDING_ID_MIGRATION].discard(entry.entry_id)
        _async_migrate_entity_ids(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
