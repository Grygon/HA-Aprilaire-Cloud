# Tests

Two tiers, both run by a single `pytest` invocation:

| File | Needs | What it covers |
|------|-------|----------------|
| `test_api.py` | `requests`, `pycognito` only | Pure client logic: MAC/zone normalization, request building, 401-retry, accessory handling, `fetch_all` aggregation. No network, no HA. |
| `test_climate.py` | HA test harness | Climate entity state mapping (mode → HVAC, setpoints, `hvac_action`, fan) and the control services (`set_temperature`, `set_fan_mode`, `set_hvac_mode`), plus sensors/binary_sensor. |
| `test_config_flow.py` | HA test harness | Config-flow discovery happy path, `invalid_auth` / `cannot_connect` errors, duplicate-device abort. |

The HA-harness tests never hit the network: `conftest.py` patches `AprilaireCloud`
with a mock that serves canned payloads captured from a real 8920W (in
`fixtures/`) and records control calls.

## Easiest way to run — the dev box

From `../devbox/`:

```bash
./run.sh test              # runs the whole suite in a throwaway HA container
./run.sh test -k config    # pass extra args straight through to pytest
./run.sh test tests/test_api.py -v
```

This runs pytest inside a disposable copy of the same Home Assistant image the
dev box uses, so it matches the real HA version and never touches your host
Python (which is pinned to `mcp==1.9.4` for the MCP servers). First run installs
the harness; a mounted pip cache makes repeat runs fast.

## Running directly (if you already have a HA dev env)

```bash
cd ..                                   # repo root (has custom_components/ + pytest.ini)
pip install -r requirements-test.txt
pytest
```
