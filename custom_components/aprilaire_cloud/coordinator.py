"""DataUpdateCoordinator for the Aprilaire (Cloud) integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HassJob, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later, async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AprilaireAuthError, AprilaireCloud, AprilaireError
from .const import (
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_ZONE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_ZONE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Seconds to wait after a write before re-polling, so the device (which polls the
# cloud on its own ~10-20s cadence) has time to apply and report the new value.
OPTIMISTIC_RECONCILE_DELAY = 25


class AprilaireDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the Aprilaire cloud once per interval for one device/zone."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = AprilaireCloud(entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
        self.device_id: str = entry.data[CONF_DEVICE_ID]
        self.zone: str = entry.data.get(CONF_ZONE, DEFAULT_ZONE)
        self.device_info_raw: dict[str, Any] = {}
        # Learned on the first poll: skip the dehumidifier request if absent.
        self._has_dehumidifier = True
        # Pending post-write reconcile timer (cancel_on_shutdown so it never
        # lingers past unload, and re-scheduling cancels the previous one).
        self._reconcile_unsub: CALLBACK_TYPE | None = None
        self._reconcile_job = HassJob(
            self._async_reconcile,
            "aprilaire_cloud reconcile",
            cancel_on_shutdown=True,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.device_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_setup(self) -> None:
        """One-time setup: authenticate and grab static device/hardware info."""
        try:
            await self.hass.async_add_executor_job(self.api.authenticate)
            self.device_info_raw = await self.hass.async_add_executor_job(
                self.api.get_device_status, self.device_id
            )
        except AprilaireAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AprilaireError as err:
            raise UpdateFailed(str(err)) from err

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.hass.async_add_executor_job(
                self.api.fetch_all,
                self.device_id,
                self.zone,
                self._has_dehumidifier,
            )
        except AprilaireAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AprilaireError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # requests errors etc.
            raise UpdateFailed(f"Error communicating with Aprilaire cloud: {err}") from err

        # After the first successful poll, stop asking for a dehumidifier we don't have.
        if data.get("dehumidifier") is None:
            self._has_dehumidifier = False
        return data

    async def async_set_thermostat(self, **settings: Any) -> None:
        """Push a settings change, optimistically reflect it, then reconcile later.

        The thermostat only checks in with the cloud every ~10-20s, so an
        immediate re-poll would read back the *old* value and clobber the
        optimistic update. Instead we show the requested value right away and
        schedule a single reconciling refresh once the device has caught up.
        """
        await self.hass.async_add_executor_job(
            lambda: self.api.set_thermostat(self.device_id, self.zone, **settings)
        )
        if self.data and (zone_settings := _zone_settings(self.data, self.zone)) is not None:
            zone_settings.update(settings)
            self.async_set_updated_data(self.data)
        if self._reconcile_unsub is not None:
            self._reconcile_unsub()  # drop any still-pending reconcile from a prior write
        self._reconcile_unsub = async_call_later(
            self.hass, OPTIMISTIC_RECONCILE_DELAY, self._reconcile_job
        )

    async def async_set_humidifier(self, **settings: Any) -> None:
        """Push a humidifier change (``mode`` and/or ``autoModeSetpoint``),
        optimistically reflect it, then reconcile once the device catches up.

        Same write-lag as the thermostat: the device only reports the new value
        on its next cloud check-in, so we show it immediately and re-poll later.
        """
        await self.hass.async_add_executor_job(
            lambda: self.api.set_humidifier(self.device_id, **settings)
        )
        settings_doc = (self.data or {}).get("settings") or {}
        if (humidifier := settings_doc.get("humidifier")) is not None:
            humidifier.update(settings)
            # Turning the humidifier off makes the device report a 0 level.
            if settings.get("mode") == "off":
                humidifier["autoModeSetpoint"] = 0
            self.async_set_updated_data(self.data)
        if self._reconcile_unsub is not None:
            self._reconcile_unsub()  # drop any still-pending reconcile from a prior write
        self._reconcile_unsub = async_call_later(
            self.hass, OPTIMISTIC_RECONCILE_DELAY, self._reconcile_job
        )

    @callback
    def _async_reconcile(self, _now) -> None:
        """Re-poll after a write so the optimistic value is confirmed/corrected."""
        self._reconcile_unsub = None
        self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _schedule_refresh(self) -> None:
        """Schedule the next poll snapped to a wall-clock multiple of the interval.

        The base coordinator fires ``update_interval`` seconds after the previous
        run off the monotonic clock, so polls drift to arbitrary wall-clock
        offsets. We instead align to epoch-based boundaries, so a 60s interval
        polls at :00 every minute, a 10s interval at :00/:10/:20, and so on.
        """
        if self._update_interval_seconds is None:
            return
        if self.config_entry and self.config_entry.pref_disable_polling:
            return
        self._async_unsub_refresh()
        interval = self._update_interval_seconds
        # Seconds until the next instant that is a whole multiple of the interval
        # since the Unix epoch (which is itself aligned to :00). If we're exactly
        # on a boundary, wait a full interval rather than firing immediately.
        delay = interval - (time.time() % interval)
        self._unsub_refresh = async_track_point_in_utc_time(
            self.hass,
            self._handle_aligned_refresh,
            dt_util.utcnow() + timedelta(seconds=delay),
        )

    @callback
    def _handle_aligned_refresh(self, _now) -> None:
        """Fire a scheduled poll, mirroring the base coordinator's task creation."""
        self._unsub_refresh = None
        if self.config_entry:
            self.config_entry.async_create_background_task(
                self.hass,
                self._handle_refresh_interval(),
                name=f"{self.name} - refresh",
                eager_start=True,
            )
        else:
            self.hass.async_create_background_task(
                self._handle_refresh_interval(),
                name=f"{self.name} - refresh",
                eager_start=True,
            )


def _zone_settings(data: dict[str, Any], zone: str) -> dict[str, Any] | None:
    """Return the thermostat<ZONE> sub-dict of a settings payload, if present."""
    settings = (data or {}).get("settings") or {}
    from .api import zone_url_key

    return settings.get(f"thermostat{zone_url_key(zone)}")
