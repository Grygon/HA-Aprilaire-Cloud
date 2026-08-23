"""HA-harness tests for the config flow: discovery happy path and error handling."""

from __future__ import annotations

from homeassistant.data_entry_flow import FlowResultType

from custom_components.aprilaire_cloud.api import AprilaireAuthError, AprilaireError
from custom_components.aprilaire_cloud.const import DOMAIN

DEVICE_ID = "B4825501968E"


async def test_user_flow_single_device_creates_entry(hass, patched_cloud):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "user@example.com", "password": "secret"},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Whole Home"
    assert result["data"]["device_id"] == DEVICE_ID
    assert result["data"]["zone"] == "PZ1"
    assert result["result"].unique_id == f"{DEVICE_ID}_PZ1"


async def test_user_flow_invalid_auth(hass, patched_cloud):
    patched_cloud.authenticate.side_effect = AprilaireAuthError("bad creds")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "user@example.com", "password": "wrong"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass, patched_cloud):
    patched_cloud.authenticate.side_effect = AprilaireError("network down")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "user@example.com", "password": "secret"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_device_aborts(hass, patched_cloud, setup_integration):
    await setup_integration()  # already configured with DEVICE_ID / PZ1
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": "user@example.com", "password": "secret"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
