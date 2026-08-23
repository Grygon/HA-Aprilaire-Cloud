"""Config flow for the Aprilaire (Cloud) integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .api import (
    AprilaireAuthError,
    AprilaireCloud,
    AprilaireError,
    mac_to_device_id,
    zone_url_key,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ZONE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def _validate(hass, email: str, password: str) -> list[dict]:
    """Log in and return the account's device list. Raises on failure."""
    client = AprilaireCloud(email, password)

    def _login_and_list() -> list[dict]:
        client.authenticate()
        return client.list_devices()

    return await hass.async_add_executor_job(_login_and_list)


class AprilaireConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._devices: list[dict] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials, validate, then pick a device."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            try:
                devices = await _validate(self.hass, email, password)
            except AprilaireAuthError:
                errors["base"] = "invalid_auth"
            except AprilaireError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Aprilaire login")
                errors["base"] = "unknown"
            else:
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    self._email = email
                    self._password = password
                    self._devices = devices
                    if len(devices) == 1:
                        return await self._create_entry(devices[0])
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose which thermostat to add when the account has several."""
        if user_input is not None:
            chosen = next(
                d for d in self._devices if d["device_id"] == user_input[CONF_DEVICE_ID]
            )
            return await self._create_entry(chosen)

        options = {
            d["device_id"]: f"{d.get('room') or d['device_id']} ({d['device_id']})"
            for d in self._devices
        }
        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}),
        )

    async def _create_entry(self, device: dict) -> ConfigFlowResult:
        device_id = mac_to_device_id(device["device_id"])
        zone = zone_url_key(device.get("zone", 1))
        await self.async_set_unique_id(f"{device_id}_{zone}")
        self._abort_if_unique_id_configured()
        title = device.get("room") or f"Aprilaire {device_id}"
        return self.async_create_entry(
            title=title,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device_id,
                CONF_ZONE: zone,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Kick off re-authentication when the stored password stops working."""
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            try:
                await _validate(self.hass, self._email, password)
            except AprilaireAuthError:
                errors["base"] = "invalid_auth"
            except AprilaireError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Aprilaire reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates={CONF_PASSWORD: password}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): cv.string}),
            description_placeholders={CONF_EMAIL: self._email or ""},
            errors=errors,
        )
