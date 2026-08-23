"""Sensor platform for Aprilaire (Cloud).

These give the recorder clean, single-purpose entities to build history and
long-term statistics from (indoor temp/humidity, outdoor temp, Wi-Fi signal,
humidifier state) -- the climate entity's own attributes are not statistics-friendly.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AprilaireConfigEntry
from .entity import AprilaireEntity, sensor_reading


@dataclass(frozen=True, kw_only=True)
class AprilaireSensorDescription(SensorEntityDescription):
    """Describes an Aprilaire sensor and how to extract its value from coordinator data."""

    value_fn: Callable[[dict[str, Any]], Any]
    # Only create the entity if this returns True for the current data.
    exists_fn: Callable[[dict[str, Any]], bool] = lambda data: True


def _status(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("status") or {}


def _humidifier(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("humidifier") or {}


SENSORS: tuple[AprilaireSensorDescription, ...] = (
    AprilaireSensorDescription(
        key="indoor_temperature",
        translation_key="indoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: sensor_reading(_status(d).get("tempSensors"), "control"),
    ),
    AprilaireSensorDescription(
        key="indoor_humidity",
        translation_key="indoor_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: sensor_reading(_status(d).get("humSensors"), "control"),
    ),
    AprilaireSensorDescription(
        key="outdoor_temperature",
        translation_key="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,  # many units have no outdoor sensor
        value_fn=lambda d: sensor_reading(_status(d).get("tempSensors"), "outdoor"),
        exists_fn=lambda d: sensor_reading(_status(d).get("tempSensors"), "outdoor") is not None,
    ),
    AprilaireSensorDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: _status(d).get("wifiRSSI"),
    ),
    AprilaireSensorDescription(
        key="humidifier_status",
        translation_key="humidifier_status",
        device_class=SensorDeviceClass.ENUM,
        options=["active", "inactive"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: _humidifier(d).get("equipmentStatus"),
        exists_fn=lambda d: (d or {}).get("humidifier") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AprilaireConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aprilaire sensors that apply to this device."""
    coordinator = entry.runtime_data
    async_add_entities(
        AprilaireSensor(coordinator, description)
        for description in SENSORS
        if description.exists_fn(coordinator.data or {})
    )


class AprilaireSensor(AprilaireEntity, SensorEntity):
    """A single coordinator-derived Aprilaire sensor."""

    entity_description: AprilaireSensorDescription

    def __init__(self, coordinator, description: AprilaireSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
