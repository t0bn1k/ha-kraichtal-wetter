from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_API_URL, DEFAULT_API_URL, DOMAIN
from .coordinator import REQUESTED_SECTIONS, _split_api_key

# Every name an API key has ever been stored under. `async_setup_entry` still
# reads all three for backwards compatibility, so all three have to be redacted
# — an entry written by an older version carries a name this one no longer
# creates.
TO_REDACT = {CONF_API_KEY, "api_key", "apikey"}


def _redactor(api_key: str | None):
    """Return a function that strips the configured key out of free text.

    `async_redact_data` only looks at mapping keys, so it cannot help with a
    key that ended up inside a string — a URL's query, an error message. The
    key is known here, so the blunt approach is also the reliable one. Guards
    the same leak that 0.4.4 closed in the client.
    """

    def redact(text: str) -> str:
        return text.replace(api_key, REDACTED) if api_key else text

    return redact


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Versions before 0.4.4 stored the key in the URL's query string. Run it
    # through the splitter the client uses rather than trusting or dropping it:
    # the endpoint is worth seeing, the key is not.
    api_url, url_key = _split_api_key(entry.data.get(CONF_API_URL, DEFAULT_API_URL))

    # Same three names, same order as `async_setup_entry` — the diagnostics
    # must redact the key the client actually uses, not a different one. An
    # entry that only ever had it in the URL falls back to that one.
    api_key = (
        entry.data.get(CONF_API_KEY)
        or entry.data.get("api_key")
        or entry.data.get("apikey")
        or url_key
    )
    redact = _redactor(api_key)

    # `async_redact_data` blanks the fields named in TO_REDACT; the sweep after
    # it catches a key sitting *inside* a value, which is exactly where a
    # pre-0.4.4 entry keeps it (`api_url`). The stored URL is replaced by the
    # split one first, so an entry whose key exists nowhere else is covered too.
    entry_data = async_redact_data(dict(entry.data), TO_REDACT)
    if CONF_API_URL in entry_data:
        entry_data[CONF_API_URL] = api_url
    entry_data = {
        name: redact(value) if isinstance(value, str) else value
        for name, value in entry_data.items()
    }

    last_exception = coordinator.last_exception
    update_interval = coordinator.update_interval

    return {
        "entry": {
            "version": entry.version,
            "data": entry_data,
            "options": dict(entry.options),
        },
        "request": {
            "url": redact(api_url),
            # True means this entry predates 0.4.4 and still carries the key in
            # its URL. The client splits it off before every request, so it is
            # not a live leak — but it explains an entry that looks odd.
            "key_in_url": url_key is not None,
            "sections": list(REQUESTED_SECTIONS),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                update_interval.total_seconds() if update_interval else None
            ),
            "last_exception": (
                None
                if last_exception is None
                else {
                    "type": type(last_exception).__name__,
                    "message": redact(str(last_exception)),
                }
            ),
        },
        # Weather data carries nothing personal, but the redaction runs over it
        # too: it costs nothing, and a field the API may add later cannot then
        # quietly carry the key into a bug report.
        "api": (
            async_redact_data(coordinator.data, TO_REDACT)
            if isinstance(coordinator.data, dict)
            else coordinator.data
        ),
    }
