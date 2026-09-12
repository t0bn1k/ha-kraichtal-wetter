from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    APPLY_URL,
    CONF_API_KEY,
    CONF_API_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

# Rejects anything below the API's five-minute server-side cache instead of
# silently raising it, so the user sees why the value was not accepted.
SCAN_INTERVAL_SELECTOR = vol.All(cv.positive_int, vol.Range(min=MIN_SCAN_INTERVAL))


class KraichtalWetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # 2: entity ids follow the German names again (see async_migrate_entry).
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            data = dict(user_input)
            data[CONF_API_URL] = DEFAULT_API_URL

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title="Kraichtal Wetter", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
            description_placeholders={"apply_url": APPLY_URL},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry is None:
                return self.async_abort(reason="entry_not_found")

            new_data = dict(entry.data)
            new_data[CONF_API_KEY] = user_input[CONF_API_KEY]

            self.hass.config_entries.async_update_entry(entry, data=new_data)
            await self.hass.config_entries.async_reload(entry.entry_id)

            return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): cv.string,
                }
            ),
            description_placeholders={"apply_url": APPLY_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> KraichtalWetterOptionsFlow:
        return KraichtalWetterOptionsFlow(config_entry)

    def _get_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                # Required, not optional: the API answers 401 without a key, so
                # a setup without one would complete and land the user straight
                # in the reauth dialog. Existing entries keep working — the
                # schema only applies to a new setup.
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): SCAN_INTERVAL_SELECTOR,
            }
        )


class KraichtalWetterOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        # An entry stored below the minimum before it was
                        # enforced would otherwise pre-fill a value the schema
                        # then rejects, leaving the user with an error and no
                        # obvious cause.
                        default=max(
                            current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                            MIN_SCAN_INTERVAL,
                        ),
                    ): SCAN_INTERVAL_SELECTOR,
                }
            ),
        )
