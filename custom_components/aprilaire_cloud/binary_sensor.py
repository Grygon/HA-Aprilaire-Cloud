"""Binary sensor platform for Aprilaire (Cloud)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AprilaireConfigEntry
from .entity import AprilaireEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan-running binary sensor."""
    async_add_entities([AprilaireFanRunning(entry.runtime_data)])


class AprilaireFanRunning(AprilaireEntity, BinarySensorEntity):
    """Whether the blower fan is currently running.

    Complements the climate ``hvac_action`` (which reports HEATING/COOLING and
    thus hides the fan while the compressor runs)."""

    _attr_translation_key = "fan_running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_id}_fan_running"

    @property
    def is_on(self) -> bool | None:
        return self._status.get("isFanOn")
