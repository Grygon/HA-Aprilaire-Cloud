"""Switch platform for Aprilaire (Cloud): the humidifier on/off control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AprilaireConfigEntry
from .entity import AprilaireEntity

# Level to fall back to when turning the humidifier on with no prior level
# (the device reports 0 while off, so we can't just re-enable in place).
DEFAULT_ON_LEVEL = 1


def _has_humidifier(coordinator) -> bool:
    settings = (coordinator.data or {}).get("settings") or {}
    return settings.get("humidifier") is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the humidifier switch, if this device has a humidifier."""
    coordinator = entry.runtime_data
    if _has_humidifier(coordinator):
        async_add_entities([AprilaireHumidifierSwitch(coordinator)])


class AprilaireHumidifierSwitch(AprilaireEntity, SwitchEntity):
    """Turns the whole-home humidifier on or off (its ``mode`` setting)."""

    _attr_translation_key = "humidifier"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_id}_humidifier"

    @property
    def is_on(self) -> bool | None:
        mode = self._humidifier_settings.get("mode")
        if mode is None:
            return None
        return mode == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Re-enable at the last known level, or a sensible default if it was 0.
        level = self._humidifier_settings.get("autoModeSetpoint") or DEFAULT_ON_LEVEL
        await self.coordinator.async_set_humidifier(mode="on", autoModeSetpoint=level)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_humidifier(mode="off")
