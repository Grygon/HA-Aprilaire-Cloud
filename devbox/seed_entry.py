#!/usr/bin/env python3
"""Seed a Home Assistant config entry for aprilaire_cloud from a .env file.

Writes .storage/core.config_entries so HA sets the integration up on boot without
needing to click through the UI config flow. We deliberately write the entry at
store minor_version 1 and let HA's own migrations backfill any newer fields
(created_at, discovery_keys, subentries, ...), so this stays correct across HA
versions instead of hard-coding the current storage schema.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("'\"")
    return env


def main() -> int:
    config_dir = Path(sys.argv[1])
    env_file = Path(sys.argv[2])
    env = {**load_env(env_file), **os.environ}

    email = env.get("APRILAIRE_EMAIL")
    password = env.get("APRILAIRE_PASSWORD")
    device_id = (env.get("APRILAIRE_DEVICE_ID") or "").replace(":", "").upper()
    zone = env.get("APRILAIRE_ZONE", "PZ1")
    if not (email and password and device_id):
        print("seed: missing APRILAIRE_EMAIL/PASSWORD/DEVICE_ID; skipping seed", file=sys.stderr)
        return 0

    storage = config_dir / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    store = storage / "core.config_entries"

    unique_id = f"{device_id}_{zone}"
    entry = {
        "entry_id": uuid.uuid4().hex,
        "version": 1,
        "minor_version": 1,
        "domain": "aprilaire_cloud",
        "title": "Whole Home (dev)",
        "data": {
            "email": email,
            "password": password,
            "device_id": device_id,
            "zone": zone,
        },
        "options": {},
        "pref_disable_new_entities": False,
        "pref_disable_polling": False,
        "source": "user",
        "unique_id": unique_id,
        "disabled_by": None,
    }

    if store.exists():
        data = json.loads(store.read_text())
        entries = data.setdefault("data", {}).setdefault("entries", [])
        if any(e.get("unique_id") == unique_id for e in entries):
            print("seed: entry already present; leaving as-is")
            return 0
        entries.append(entry)
    else:
        data = {
            "version": 1,
            "minor_version": 1,
            "key": "core.config_entries",
            "data": {"entries": [entry]},
        }
        entries = data["data"]["entries"]

    store.write_text(json.dumps(data, indent=2))
    print(f"seed: wrote config entry for device {device_id} zone {zone} ({len(entries)} total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
