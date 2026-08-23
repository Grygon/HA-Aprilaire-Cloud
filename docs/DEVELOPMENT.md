# Development

## How it works / provenance

The Aprilaire cloud API is undocumented. This integration was built by
reverse-engineering the Android app and capturing live traffic:

- **Auth:** AWS Cognito (`pycognito`).
- **Control & status:** `device.aprilaire.io`.
- **Runtime history:** `tsdb.aprilaire.io`.

It is unofficial and not affiliated with Aprilaire. The API can change at any
time without notice.

### Architecture

| Module | Responsibility |
|--------|----------------|
| `api.py` | Blocking cloud client (auth, status/settings, control, runtime). Pure `requests` + `pycognito`, no HA imports. |
| `coordinator.py` | `DataUpdateCoordinator` — polls every 60 s (aligned to the wall-clock interval), runs the blocking client in an executor, handles optimistic writes + reconcile. |
| `config_flow.py` | Email/password login, device discovery/picker, reauth. |
| `climate.py` / `sensor.py` / `binary_sensor.py` / `switch.py` / `number.py` | The user-facing entities. |
| `entity.py` | Shared `CoordinatorEntity` base + `DeviceInfo`. |

Notes on behaviour worth knowing when hacking on it:

- The thermostat polls the cloud on its own ~10–20 s schedule, so an immediate
  re-poll after a write reads back the *old* value. Writes update the cache
  optimistically and schedule a single reconciling refresh
  (`OPTIMISTIC_RECONCILE_DELAY`, 25 s) instead.
- The device is natively Fahrenheit at 0.5 °F resolution; the API speaks Celsius.
  Entities report Celsius with a 0.5° step; the device rounds to its nearest
  native value.
- Zone status keys are case-sensitive and uppercase (`PZ1`, `SZ2`, …).
- Each piece of equipment (fan, heating, cooling, humidifier) is its own
  `running` binary sensor so it gets an independent on/off history and runtime.
  The climate `hvac_action` can only report one state at a time (it hides the fan
  while the compressor runs), so it isn't a substitute. Heating/cooling come from
  the `heatingStatus` / `coolingStatus` fields (`"inactive"` vs. `"comp1"` etc.);
  the humidifier from its `equipmentStatus`.
- The humidifier lives in the settings document as
  `{"mode": "on"|"off", "autoModeSetpoint": 0-7}`. `mode` is the on/off toggle
  (the switch); `autoModeSetpoint` is the 1–7 dial level (the number). The device
  reports `autoModeSetpoint: 0` while the humidifier is off, so the number
  surfaces that as unknown and turning the switch on re-enables at the last level
  (or 1). Writes go through the same optimistic-reconcile path as the thermostat.
- Polling is aligned to wall-clock multiples of the scan interval by overriding
  the coordinator's `_schedule_refresh` (the base fires a fixed interval after the
  previous run off the monotonic clock, which drifts off the clock). A 60 s
  interval polls at `:00`, a 10 s interval at `:00/:10/:20`, etc.

## Dev box

A throwaway Home Assistant instance for testing lives in [`../devbox/`](../devbox/)
(rootless podman). It copies the integration in, seeds a config entry from
`../.env` (so it sets up headlessly — no clicking through the UI), and starts HA:

```bash
cd devbox
./run.sh up        # sync + seed + start   -> http://localhost:8123
./run.sh logs      # follow logs
./run.sh restart   # re-sync code changes and restart
./run.sh down      # stop & remove the container
./run.sh reset     # wipe the config dir for a clean slate
```

The `devbox/config/` directory holds runtime state including credentials and is
git-ignored. Open http://localhost:8123 and onboard (create a local account) to
click around the UI; the thermostat is already set up from the seeded entry.

## Tests

```bash
cd devbox
./run.sh test                 # full pytest suite in a throwaway HA container
./run.sh test -k config -v    # extra args pass straight through to pytest
```

Unit tests (`tests/test_api.py`) cover the pure cloud-client logic; HA-harness
tests (`tests/test_climate.py`, `tests/test_config_flow.py`) drive the real
entities and config flow against mocked API payloads captured from a live 8920W.
See [`../tests/README.md`](../tests/README.md) for details.
