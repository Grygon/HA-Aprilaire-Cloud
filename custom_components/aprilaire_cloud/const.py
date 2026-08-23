"""Constants for the Aprilaire (Cloud) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "aprilaire_cloud"

# Config entry keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"
CONF_ZONE = "zone"

DEFAULT_ZONE = "PZ1"

# How often to poll the cloud. The thermostat itself only checks in with the
# cloud every ~10-20s, so anything faster than a minute is wasted requests.
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

# AWS Cognito pool backing account.aprilaire.io (reverse-engineered from the app).
COGNITO_USER_POOL_ID = "us-west-2_skfkpmVv6"
COGNITO_CLIENT_ID = "3aiakr6qdoqtajv7qgtapecerg"
COGNITO_REGION = "us-west-2"

DEVICE_API = "https://device.aprilaire.io"
TSDB_API = "https://tsdb.aprilaire.io"

MANUFACTURER = "Aprilaire"

# Aprilaire mode string <-> HA HVACMode
MODE_OFF = "off"
MODE_HEAT = "heat"
MODE_COOL = "cool"
MODE_AUTO = "auto"  # auto-changeover, both setpoints active -> HA HEAT_COOL

# Aprilaire fan string <-> HA fan mode
FAN_AUTO = "auto"
FAN_ON = "on"
FAN_CIRC = "circ"
FAN_CIRCULATE = "circulate"  # friendlier HA-facing label for "circ"
