"""Shared pytest fixtures for the aprilaire_cloud test suite.

The HA-harness tests never touch the network: they patch ``AprilaireCloud`` with a
MagicMock that serves canned payloads (captured from a real 8920W) and records
control calls. The pure client tests in ``test_api.py`` don't use these fixtures.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

DEVICE_ID = "B4825501968E"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA load the aprilaire_cloud custom integration during tests."""
    yield


@pytest.fixture
def payloads() -> dict:
    return {
        "settings": _load("settings.json"),
        "status": _load("status.json"),
        "humidifier": _load("humidifier.json"),
        "device_status": _load("device_status.json"),
        "hierarchy": _load("hierarchy.json"),
    }


@pytest.fixture
def cloud_state(payloads) -> dict:
    """The mutable 'current' device state a test can tweak *before* setup to
    exercise different modes (e.g. flip settings.mode to 'auto')."""
    return {
        "settings": copy.deepcopy(payloads["settings"]),
        "status": copy.deepcopy(payloads["status"]),
        "humidifier": copy.deepcopy(payloads["humidifier"]),
        "dehumidifier": None,
    }


@pytest.fixture
def mock_cloud(cloud_state, payloads) -> MagicMock:
    """A stand-in for AprilaireCloud that serves cloud_state and records writes."""
    cloud = MagicMock()
    cloud.authenticate.return_value = None
    cloud.get_device_status.return_value = payloads["device_status"]
    cloud.list_devices.return_value = [
        {
            "device_id": DEVICE_ID,
            "zone": 1,
            "access": "manage",
            "location": "Home",
            "room": "Whole Home",
        }
    ]

    def fetch_all(device_id, zone="PZ1", include_dehumidifier=True):
        return copy.deepcopy(cloud_state)

    cloud.fetch_all.side_effect = fetch_all
    cloud.set_thermostat.return_value = None
    return cloud


@pytest.fixture
def patched_cloud(mock_cloud):
    """Patch the client into both the coordinator and the config flow."""
    with (
        patch(
            "custom_components.aprilaire_cloud.coordinator.AprilaireCloud",
            return_value=mock_cloud,
        ),
        patch(
            "custom_components.aprilaire_cloud.config_flow.AprilaireCloud",
            return_value=mock_cloud,
        ),
    ):
        yield mock_cloud


@pytest.fixture
def setup_integration(hass, patched_cloud):
    """Return an async callable that sets up a config entry and returns it.

    Callable form (rather than a plain fixture) so a test can mutate
    ``cloud_state`` first, then set up against the modified state.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.aprilaire_cloud.const import DOMAIN

    async def _setup() -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "email": "user@example.com",
                "password": "secret",
                "device_id": DEVICE_ID,
                "zone": "PZ1",
            },
            unique_id=f"{DEVICE_ID}_PZ1",
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup
