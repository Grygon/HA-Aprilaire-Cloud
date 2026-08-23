"""Thin synchronous client for the (unofficial) Aprilaire cloud API.

Reverse-engineered from the Android app (Capacitor/Ionic bundle + mitmproxy
capture). Auth is AWS Cognito; device control/status is device.aprilaire.io;
historical runtime data is tsdb.aprilaire.io.

Everything here is blocking (requests + pycognito). Home Assistant must call it
through ``hass.async_add_executor_job`` -- see ``coordinator.py``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from pycognito import Cognito
from pycognito.exceptions import ForceChangePasswordException

from .const import (
    COGNITO_CLIENT_ID,
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
    DEVICE_API,
    TSDB_API,
)

_LOGGER = logging.getLogger(__name__)

_ZONE_KEYS = {1: "PZ1", 2: "SZ2", 3: "SZ3"}


class AprilaireError(Exception):
    """Base error for the Aprilaire cloud client."""


class AprilaireAuthError(AprilaireError):
    """Raised when authentication fails (bad credentials / expired refresh)."""


def mac_to_device_id(mac: str) -> str:
    """Normalize a MAC (any case, with or without colons) to the API's device id."""
    return mac.replace(":", "").replace("-", "").upper()


def zone_url_key(zone: Any) -> str:
    """Normalize 1/2/3 or 'PZ1'/'SZ2'/'SZ3' to the uppercase form the status
    endpoint's path segment requires. Lowercase / numeric forms 500 the backend."""
    s = str(zone).strip().upper()
    if s.startswith(("PZ", "SZ")):
        return s
    return _ZONE_KEYS[int(s)]


def zone_number(zone: Any) -> int:
    """Normalize a zone to its plain number (1/2/3) for settings-body keys / tsdb."""
    s = str(zone).strip().upper()
    if s.startswith(("PZ", "SZ")):
        s = s[2:]
    return int(s)


class AprilaireCloud:
    """Blocking Aprilaire cloud client scoped to a single account.

    A single instance holds one authenticated Cognito session and can address any
    device on the account. It transparently refreshes the id token, and re-runs the
    full SRP login if the refresh token has expired.
    """

    def __init__(self, email: str, password: str, session: requests.Session | None = None) -> None:
        self._email = email
        self._password = password
        self._session = session or requests.Session()
        self._cognito: Cognito | None = None

    # -- auth -----------------------------------------------------------------

    def authenticate(self) -> None:
        """Perform the initial SRP login. Raises AprilaireAuthError on bad creds."""
        cognito = Cognito(
            COGNITO_USER_POOL_ID,
            COGNITO_CLIENT_ID,
            username=self._email,
            user_pool_region=COGNITO_REGION,
        )
        try:
            cognito.authenticate(password=self._password)
        except ForceChangePasswordException as err:
            raise AprilaireAuthError("Account requires a password change") from err
        except Exception as err:  # botocore ClientError et al.
            raise AprilaireAuthError(f"Authentication failed: {err}") from err
        self._cognito = cognito

    def _headers(self) -> dict[str, str]:
        """Return auth headers, refreshing / re-authenticating as needed."""
        if self._cognito is None:
            self.authenticate()
        assert self._cognito is not None
        try:
            self._cognito.check_token()  # refreshes id_token in place if expired
        except Exception as err:  # refresh token expired / revoked -> full re-login
            _LOGGER.debug("Token refresh failed (%s); re-authenticating", err)
            self.authenticate()
        return {
            "Authorization": f"Bearer {self._cognito.id_token}",
            "Content-Type": "application/json",
        }

    # -- low-level HTTP -------------------------------------------------------

    def _request(self, method: str, url: str, *, timeout: float = 15, **kwargs) -> requests.Response:
        resp = self._session.request(method, url, headers=self._headers(), timeout=timeout, **kwargs)
        if resp.status_code in (401, 403):
            # token may have gone stale between refresh and use; retry once fresh.
            self.authenticate()
            resp = self._session.request(method, url, headers=self._headers(), timeout=timeout, **kwargs)
        resp.raise_for_status()
        return resp

    # -- account / discovery --------------------------------------------------

    def get_hierarchy(self) -> dict:
        """Account tree: locations -> rooms -> devices (deviceId, zone, access)."""
        return self._request("GET", f"{DEVICE_API}/hierarchy").json()

    def list_devices(self) -> list[dict]:
        """Flatten the hierarchy into a list of devices with location/room context."""
        devices: list[dict] = []
        for loc in self.get_hierarchy().get("locations", []):
            for room in loc.get("rooms", []):
                for dev in room.get("devices", []):
                    devices.append(
                        {
                            "device_id": dev.get("deviceId"),
                            "zone": dev.get("zone", 1),
                            "access": dev.get("access"),
                            "location": loc.get("name"),
                            "room": room.get("name"),
                        }
                    )
        return devices

    # -- per-device status / settings ----------------------------------------

    def get_device_status(self, device_id: str) -> dict:
        """Hardware/firmware/model info (e.g. model '8920W_GS')."""
        return self._request("GET", f"{DEVICE_API}/{device_id}/status").json()

    def get_thermostat_status(self, device_id: str, zone: Any = "PZ1") -> dict:
        """Live sensor readings + equipment state for one zone."""
        return self._request(
            "GET", f"{DEVICE_API}/{device_id}/status/thermostat/{zone_url_key(zone)}"
        ).json()

    def get_humidifier_status(self, device_id: str) -> dict | None:
        return self._normalize_accessory(
            self._request("GET", f"{DEVICE_API}/{device_id}/status/humidifier").json()
        )

    def get_dehumidifier_status(self, device_id: str) -> dict | None:
        return self._normalize_accessory(
            self._request("GET", f"{DEVICE_API}/{device_id}/status/dehumidifier").json()
        )

    @staticmethod
    def _normalize_accessory(value: Any) -> dict | None:
        """Equipment that isn't physically present answers 200 with a
        {'message': 'Equipment does not belong...'} body. Treat that as absent."""
        if isinstance(value, dict) and "message" in value and "equipmentStatus" not in value:
            return None
        return value

    def get_settings(self, device_id: str) -> dict:
        """Current setpoints/mode/fan/hold config (the write-side mirror)."""
        return self._request("GET", f"{DEVICE_API}/{device_id}/settings").json()

    def set_thermostat(self, device_id: str, zone: Any = "PZ1", **settings: Any) -> None:
        """PATCH one or more of: heat=, cool= (Celsius), mode=, fan=."""
        body = {f"thermostat{zone_url_key(zone)}": settings}
        self._request(
            "PATCH", f"{DEVICE_API}/{device_id}/settings", data=json.dumps(body)
        )

    # -- history --------------------------------------------------------------

    def get_heating_cooling_runtime(
        self, device_id: str, hours: int = 24, zone: Any = "PZ1", bucket_width: str = "1 hour"
    ) -> dict:
        now = datetime.now(timezone.utc).astimezone()
        frm = now - timedelta(hours=hours)
        body = {
            "generic": [
                {
                    "queryName": "GetHeatingCoolingStateTimelineInRange",
                    "params": {
                        "bucket_width": bucket_width,
                        "from": frm.isoformat(timespec="milliseconds"),
                        "to": now.isoformat(timespec="milliseconds"),
                        "device_id": device_id,
                        "timezone": str(now.tzinfo),
                        "zone": str(zone_number(zone)),
                    },
                }
            ]
        }
        return self._request("POST", f"{TSDB_API}/V2/query", data=json.dumps(body)).json()

    # -- aggregate ------------------------------------------------------------

    def fetch_all(
        self, device_id: str, zone: Any = "PZ1", include_dehumidifier: bool = True
    ) -> dict:
        """One coordinator-poll's worth of data: settings + live status + accessories.

        ``include_dehumidifier`` lets the coordinator skip the extra request once
        it has learned this device has no dehumidifier.
        """
        data: dict[str, Any] = {
            "settings": self.get_settings(device_id),
            "status": self.get_thermostat_status(device_id, zone),
            "humidifier": self.get_humidifier_status(device_id),
        }
        data["dehumidifier"] = (
            self.get_dehumidifier_status(device_id) if include_dehumidifier else None
        )
        return data
