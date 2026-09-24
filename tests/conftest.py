"""Shared fixtures for the Kraichtal Wetter tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.core import HomeAssistant

import custom_components

# pytest-homeassistant-custom-component ships a regular `custom_components`
# package of its own (testing_config/). A regular package wins over our
# namespace package wherever it sits on sys.path, so ours would be invisible.
# Appending the repo's directory makes both importable.
_REPO_COMPONENTS = str(Path(__file__).parent.parent / "custom_components")
if _REPO_COMPONENTS not in custom_components.__path__:
    custom_components.__path__.append(_REPO_COMPONENTS)

from custom_components.kraichtal_wetter.const import (
    CONF_API_KEY,
    CONF_API_URL,
    DEFAULT_API_URL,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"

API_KEY = "test-key-9f3a1c"

# A real response from 24.09.2026, 07:51 — see tests/fixtures/.
_RESPONSE = json.loads((Path(__file__).parent / "fixtures" / "response.json").read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load integrations from custom_components/."""


@pytest.fixture
def api_response() -> dict[str, Any]:
    """Return a fresh copy of the recorded API response, safe to modify."""
    return copy.deepcopy(_RESPONSE)


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker, api_response: dict[str, Any]) -> AiohttpClientMocker:
    """Answer every request to the API with the recorded response."""
    aioclient_mock.get(DEFAULT_API_URL, json=api_response)
    return aioclient_mock


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a current (version 2) config entry, added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kraichtal Wetter",
        unique_id=DOMAIN,
        version=2,
        data={CONF_API_KEY: API_KEY, CONF_API_URL: DEFAULT_API_URL},
    )
    entry.add_to_hass(hass)
    return entry


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set the entry up and wait until every platform has settled."""
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def respond_with(aioclient_mock: AiohttpClientMocker, **kwargs: Any) -> None:
    """Replace whatever the API mock answered before."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(DEFAULT_API_URL, **kwargs)
