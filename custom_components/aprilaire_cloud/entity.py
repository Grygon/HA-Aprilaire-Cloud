"""Shared base entity for the Aprilaire (Cloud) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AprilaireDataUpdateCoordinator


class AprilaireEntity(CoordinatorEntity[AprilaireDataUpdateCoordinator]):
    """Base entity: wires up the shared DeviceInfo and coordinator access."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AprilaireDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._device_id = coordinator.device_id
        info = coordinator.device_info_raw or {}
        room = None
        # Prefer the room/location name discovered from the settings payload.
        settings = (coordinator.data or {}).get("settings") or {}
        for key in settings:
            if key.startswith("thermostat"):
                room = settings[key].get("room")
                break
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            model=info.get("model"),
            name=room or "Aprilaire Thermostat",
            hw_version=info.get("hardwareRev"),
            sw_version=info.get("firmwareRev"),
            serial_number=self._device_id,
        )

    @property
    def _status(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("status") or {}

    @property
    def _settings(self) -> dict[str, Any]:
        """The thermostat<ZONE> sub-dict of the settings payload."""
        from .api import zone_url_key

        settings = (self.coordinator.data or {}).get("settings") or {}
        return settings.get(f"thermostat{zone_url_key(self.coordinator.zone)}") or {}


def sensor_reading(sensors: list[dict] | None, sensor_type: str) -> Any:
    """Pull a specific sensor's ``reading`` by its ``type`` from a sensor list."""
    for sensor in sensors or []:
        if sensor.get("type") == sensor_type:
            return sensor.get("reading")
    return None
