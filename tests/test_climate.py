"""HA-harness tests for the climate entity: state mapping and control services."""

from __future__ import annotations

import pytest

ENTITY = "climate.whole_home"
DEVICE_ID = "B4825501968E"


async def test_climate_state(hass, setup_integration):
    await setup_integration()
    state = hass.states.get(ENTITY)
    assert state is not None
    assert state.state == "cool"
    assert state.attributes["current_temperature"] == 21.0
    assert state.attributes["current_humidity"] == 68
    assert state.attributes["temperature"] == 21.5  # cool setpoint in cool mode
    assert state.attributes["fan_mode"] == "on"
    assert state.attributes["hvac_action"] == "cooling"


async def test_set_temperature_sets_cool_setpoint(hass, setup_integration, patched_cloud):
    await setup_integration()
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": ENTITY, "temperature": 22.0},
        blocking=True,
    )
    patched_cloud.set_thermostat.assert_called_with(DEVICE_ID, "PZ1", cool=22.0)


async def test_set_fan_mode(hass, setup_integration, patched_cloud):
    await setup_integration()
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": ENTITY, "fan_mode": "auto"},
        blocking=True,
    )
    patched_cloud.set_thermostat.assert_called_with(DEVICE_ID, "PZ1", fan="auto")


async def test_circulate_fan_mode_maps_to_circ(hass, setup_integration, patched_cloud):
    await setup_integration()
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": ENTITY, "fan_mode": "circulate"},
        blocking=True,
    )
    patched_cloud.set_thermostat.assert_called_with(DEVICE_ID, "PZ1", fan="circ")


async def test_set_hvac_mode_off(hass, setup_integration, patched_cloud):
    await setup_integration()
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": ENTITY, "hvac_mode": "off"},
        blocking=True,
    )
    patched_cloud.set_thermostat.assert_called_with(DEVICE_ID, "PZ1", mode="off")


async def test_heat_cool_uses_temperature_range(hass, cloud_state, setup_integration, patched_cloud):
    # Flip the device into auto-changeover *before* setup.
    cloud_state["settings"]["thermostatPZ1"]["mode"] = "auto"
    await setup_integration()

    state = hass.states.get(ENTITY)
    assert state.state == "heat_cool"
    assert state.attributes["target_temp_low"] == 20.0   # heat setpoint
    assert state.attributes["target_temp_high"] == 21.5  # cool setpoint
    assert state.attributes.get("temperature") is None

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": ENTITY, "target_temp_low": 19.0, "target_temp_high": 23.0},
        blocking=True,
    )
    patched_cloud.set_thermostat.assert_called_with(DEVICE_ID, "PZ1", heat=19.0, cool=23.0)


async def test_sensors_and_binary_sensor(hass, setup_integration):
    await setup_integration()
    assert hass.states.get("sensor.whole_home_indoor_temperature").state == "21.0"
    assert hass.states.get("sensor.whole_home_indoor_humidity").state == "68"
    assert hass.states.get("sensor.whole_home_humidifier").state == "inactive"
    assert hass.states.get("binary_sensor.whole_home_fan").state == "off"


async def test_fan_running_binary_sensor_true(hass, cloud_state, setup_integration):
    cloud_state["status"]["isFanOn"] = True
    await setup_integration()
    assert hass.states.get("binary_sensor.whole_home_fan").state == "on"
