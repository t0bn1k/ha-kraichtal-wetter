from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, WEBSITE_URL


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """The one device every entity of an entry belongs to."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Kraichtal Wetter",
        manufacturer="Kraichtal Wetter",
        model="Kraichtal Wetter Station",
        configuration_url=WEBSITE_URL,
    )
