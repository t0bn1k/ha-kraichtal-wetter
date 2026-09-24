from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from aiohttp import ClientError, ClientResponseError

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    APPLY_URL,
    CONF_API_KEY,
    CONF_API_URL,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .coordinator import AUTH_ERROR_STATUSES, KraichtalWetterClient

_LOGGER = logging.getLogger(__name__)

# Rejects anything below the API's five-minute server-side cache instead of
# silently raising it, so the user sees why the value was not accepted.
SCAN_INTERVAL_SELECTOR = vol.All(cv.positive_int, vol.Range(min=MIN_SCAN_INTERVAL))


async def _async_validate_key(hass: HomeAssistant, api_key: str) -> str | None:
    """Try the key against the API; return an error key for the form, or None.

    Without this a mistyped key completes the setup, fails the first refresh
    with 403 and drops the user straight into reauth — which then accepted the
    next wrong key just as blindly.
    """
    client = KraichtalWetterClient(DEFAULT_API_URL, api_key, async_get_clientsession(hass))
    try:
        # async_get_data, not async_update: the latter logs "starting reauth"
        # on a rejected key, which is wrong while the user is still typing.
        await client.async_get_data()
    except ClientResponseError as err:
        # Status only — the error's string form carries the request URL (see
        # coordinator.py). The key is never in that URL, but keep the habit.
        if err.status in AUTH_ERROR_STATUSES:
            return "invalid_auth"
        _LOGGER.debug("API key check failed with HTTP %s", err.status)
        return "cannot_connect"
    except (ClientError, TimeoutError, UpdateFailed) as err:
        _LOGGER.debug("API key check failed: %s", type(err).__name__)
        return "cannot_connect"
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Unexpected error while checking the API key: %s", type(err).__name__)
        return "unknown"
    return None


class KraichtalWetterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # 2: entity ids follow the German names again (see async_migrate_entry).
    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            error = await _async_validate_key(self.hass, user_input[CONF_API_KEY])
            if error is None:
                data = dict(user_input)
                data[CONF_API_URL] = DEFAULT_API_URL
                return self.async_create_entry(title="Kraichtal Wetter", data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(self._get_schema(), user_input),
            errors=errors,
            description_placeholders={"apply_url": APPLY_URL},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _async_validate_key(self.hass, user_input[CONF_API_KEY])
            if error is None:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_API_KEY: user_input[CONF_API_KEY]},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): cv.string,
                }
            ),
            errors=errors,
            description_placeholders={"apply_url": APPLY_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> KraichtalWetterOptionsFlow:
        return KraichtalWetterOptionsFlow()

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


class KraichtalWetterOptionsFlow(config_entries.OptionsFlowWithReload):
    # WithReload: the interval is only read in async_setup_entry, so without a
    # reload a changed value silently waited for the next restart.

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # The setup form stored the interval in `data`; options take over once
        # saved here (same order as async_setup_entry).
        entry = self.config_entry
        current = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
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
                        default=max(current, MIN_SCAN_INTERVAL),
                    ): SCAN_INTERVAL_SELECTOR,
                }
            ),
        )
