"""Binary sensor platform for Aprilaire (Cloud).

One RUNNING binary sensor per piece of equipment (fan, heating, cooling,
humidifier) so each gets its own on/off history, logbook entries, and
runtime -- the climate entity's single ``hvac_action`` can only report one of
them at a time (it hides the fan while the compressor runs, etc.)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AprilaireConfigEntry
from .entity import AprilaireEntity


@dataclass(frozen=True, kw_only=True)
class AprilaireBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a binary sensor and how to derive its state from coordinator data."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    # Only create the entity if this returns True for the current data.
    exists_fn: Callable[[dict[str, Any]], bool] = lambda data: True


def _status(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("status") or {}


def _humidifier(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("humidifier") or {}


def _equipment_running(status: Any) -> bool | None:
    """A ``*Status`` field ('inactive' / 'comp1' / ...) as a running bool.

    Returns None when the field is absent so the entity reads 'unknown' rather
    than falsely 'off'."""
    if status is None:
        return None
    return status != "inactive"


BINARY_SENSORS: tuple[AprilaireBinarySensorDescription, ...] = (
    AprilaireBinarySensorDescription(
        key="fan_running",
        translation_key="fan_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _status(d).get("isFanOn"),
    ),
    AprilaireBinarySensorDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _equipment_running(_status(d).get("heatingStatus")),
    ),
    AprilaireBinarySensorDescription(
        key="cooling",
        translation_key="cooling",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _equipment_running(_status(d).get("coolingStatus")),
    ),
    AprilaireBinarySensorDescription(
        key="humidifier_running",
        translation_key="humidifier_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda d: _equipment_running(_humidifier(d).get("equipmentStatus")),
        exists_fn=lambda d: (d or {}).get("humidifier") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the equipment-running binary sensors that apply to this device."""
    coordinator = entry.runtime_data
    async_add_entities(
        AprilaireBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.exists_fn(coordinator.data or {})
    )


class AprilaireBinarySensor(AprilaireEntity, BinarySensorEntity):
    """A single coordinator-derived RUNNING binary sensor."""

    entity_description: AprilaireBinarySensorDescription

    def __init__(self, coordinator, description: AprilaireBinarySensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data or {})
