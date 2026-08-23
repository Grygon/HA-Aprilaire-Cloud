"""Unit tests for the pure Aprilaire cloud client (no HA, no network).

These mock HTTP at the session boundary, so they assert the client's own logic:
zone/id normalization, request building, accessory handling, auth retry, and the
fetch_all aggregation.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from custom_components.aprilaire_cloud.api import (
    AprilaireCloud,
    mac_to_device_id,
    zone_number,
    zone_url_key,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("b4:82:55:01:96:8e", "B4825501968E"),
        ("B4-82-55-01-96-8E", "B4825501968E"),
        ("B4825501968E", "B4825501968E"),
    ],
)
def test_mac_to_device_id(raw, expected):
    assert mac_to_device_id(raw) == expected


@pytest.mark.parametrize(
    "zone,expected",
    [(1, "PZ1"), ("1", "PZ1"), ("PZ1", "PZ1"), (2, "SZ2"), ("sz3", "SZ3")],
)
def test_zone_url_key(zone, expected):
    assert zone_url_key(zone) == expected


@pytest.mark.parametrize("zone,expected", [(1, 1), ("PZ1", 1), ("SZ3", 3), ("2", 2)])
def test_zone_number(zone, expected):
    assert zone_number(zone) == expected


def test_normalize_accessory_absent():
    absent = {"message": "Equipment does not belong to the device."}
    assert AprilaireCloud._normalize_accessory(absent) is None


def test_normalize_accessory_present():
    present = {"equipmentStatus": "inactive", "waterPanelService": {"remaining": 100}}
    assert AprilaireCloud._normalize_accessory(present) == present


class _FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = {} if payload is None else payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _client_without_auth() -> AprilaireCloud:
    client = AprilaireCloud("user@example.com", "secret")
    client._headers = MagicMock(return_value={})  # skip real Cognito auth
    return client


def test_set_thermostat_builds_zone_body():
    client = _client_without_auth()
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, data=kwargs.get("data"))
        return _FakeResponse(200)

    client._session.request = fake_request
    client.set_thermostat("DEV123", "PZ1", cool=21.1, mode="cool")

    assert captured["method"] == "PATCH"
    assert captured["url"].endswith("/DEV123/settings")
    assert json.loads(captured["data"]) == {"thermostatPZ1": {"cool": 21.1, "mode": "cool"}}


def test_request_retries_once_on_401():
    client = _client_without_auth()
    client.authenticate = MagicMock()
    responses = [_FakeResponse(401), _FakeResponse(200, {"ok": True})]
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url))
        return responses[len(calls) - 1]

    client._session.request = fake_request
    result = client._request("GET", "https://example/x")

    assert result.json() == {"ok": True}
    assert client.authenticate.called
    assert len(calls) == 2


def test_fetch_all_aggregates_and_can_skip_dehumidifier():
    client = _client_without_auth()
    client.get_settings = MagicMock(return_value={"s": 1})
    client.get_thermostat_status = MagicMock(return_value={"t": 1})
    client.get_humidifier_status = MagicMock(return_value={"h": 1})
    client.get_dehumidifier_status = MagicMock(return_value=None)

    data = client.fetch_all("DEV123", "PZ1", include_dehumidifier=False)

    assert set(data) == {"settings", "status", "humidifier", "dehumidifier"}
    assert data["settings"] == {"s": 1}
    assert data["dehumidifier"] is None
    client.get_dehumidifier_status.assert_not_called()


def test_fetch_all_includes_dehumidifier_when_requested():
    client = _client_without_auth()
    client.get_settings = MagicMock(return_value={})
    client.get_thermostat_status = MagicMock(return_value={})
    client.get_humidifier_status = MagicMock(return_value={})
    client.get_dehumidifier_status = MagicMock(return_value={"equipmentStatus": "on"})

    data = client.fetch_all("DEV123", "PZ1", include_dehumidifier=True)

    assert data["dehumidifier"] == {"equipmentStatus": "on"}
    client.get_dehumidifier_status.assert_called_once()
