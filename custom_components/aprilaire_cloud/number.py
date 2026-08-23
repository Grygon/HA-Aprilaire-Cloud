"""Number platform for Aprilaire (Cloud): the humidifier level (1-7)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AprilaireConfigEntry
from .entity import AprilaireEntity

HUMIDIFIER_MIN_LEVEL = 1
HUMIDIFIER_MAX_LEVEL = 7


def _has_humidifier(coordinator) -> bool:
    settings = (coordinator.data or {}).get("settings") or {}
    return settings.get("humidifier") is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the humidifier level control, if this device has a humidifier."""
    coordinator = entry.runtime_data
    if _has_humidifier(coordinator):
        async_add_entities([AprilaireHumidifierLevel(coordinator)])


class AprilaireHumidifierLevel(AprilaireEntity, NumberEntity):
    """The humidifier's 1-7 dial level (Aprilaire's ``autoModeSetpoint``).

    Setting a level implies turning the humidifier on; the device reports a level
    of 0 while it is off, which we surface as unknown rather than an out-of-range 0.
    """

    _attr_translation_key = "humidifier_level"
    _attr_native_min_value = HUMIDIFIER_MIN_LEVEL
    _attr_native_max_value = HUMIDIFIER_MAX_LEVEL
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_id}_humidifier_level"

    @property
    def native_value(self) -> float | None:
        level = self._humidifier_settings.get("autoModeSetpoint")
        if not level:  # None or 0 (humidifier off) -> no meaningful level
            return None
        return level

    async def async_set_native_value(self, value: float) -> None:
        # Selecting a level turns the humidifier on at that level.
        await self.coordinator.async_set_humidifier(
            mode="on", autoModeSetpoint=int(value)
        )
