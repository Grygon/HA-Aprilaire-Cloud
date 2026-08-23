# Aprilaire (Cloud) — Home Assistant integration

A **cloud-polling** Home Assistant custom integration for legacy Wi-Fi Aprilaire
thermostats (e.g. the **8920W**) that have **no local API** and only work through
Aprilaire's cloud. It talks to the same backend the Aprilaire mobile app uses.

> If you have a newer Aprilaire *Home Automation* (8800-series) or *Zone Control*
> (6000-series) thermostat, use the **built-in** [`aprilaire`](https://www.home-assistant.io/integrations/aprilaire/)
> integration instead — it talks to the thermostat locally and is much better.
> This project exists only for the older cloud-only models that the local
> integration cannot reach.

## What you get

- **Climate entity** — current temperature & humidity, heat/cool/auto/off modes,
  single or dual (heat + cool) setpoints, fan mode (auto / on / circulate), and
  live HVAC action (heating / cooling / fan / idle).
- **Sensors** — indoor temperature, indoor humidity, outdoor temperature (if a
  sensor is present), Wi-Fi signal, and humidifier status. All carry the right
  `device_class`/`state_class`, so Home Assistant's **History** and **long-term
  Statistics** give you the historical charts automatically.
- **Binary sensor** — fan running.

### About history

Aprilaire's cloud keeps **no** server-side history for temperature, humidity, or
fan state (only heating/cooling *runtime duration*). This integration instead
lets Home Assistant's own recorder build history from the 60-second polls — which
is what the HA History and Statistics dashboards are designed for.

## Installation

**HACS (custom repository):**
1. HACS → ⋮ → *Custom repositories* → add this repo, category *Integration*.
2. Install **Aprilaire (Cloud)**, then restart Home Assistant.

**Manual:**
Copy `custom_components/aprilaire_cloud` into your HA `config/custom_components/`
directory and restart.

## Setup

*Settings → Devices & Services → Add Integration → Aprilaire (Cloud)*, then sign
in with your Aprilaire app email and password. Thermostats on the account are
discovered automatically; if you have more than one, you'll be asked which to add.

## How it works / provenance

The Aprilaire cloud API is undocumented. This integration was built by
reverse-engineering the Android app and capturing live traffic:

- **Auth:** AWS Cognito (`pycognito`).
- **Control & status:** `device.aprilaire.io`.
- **Runtime history:** `tsdb.aprilaire.io`.

It is unofficial and not affiliated with Aprilaire. The API can change at any
time without notice.

## Development

A throwaway Home Assistant instance for testing lives in [`devbox/`](devbox/)
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

## Notes & limitations

- The thermostat polls the cloud on its own schedule, so a setpoint change can
  take ~10–20 s to take physical effect. The UI updates optimistically and then
  reconciles on the next poll.
- The device is natively Fahrenheit at 0.5 °F resolution; Celsius setpoints are
  rounded to the nearest native value by the device.
- Cloud-only: if Aprilaire's servers or your internet are down, the thermostat
  is unreachable from Home Assistant.
