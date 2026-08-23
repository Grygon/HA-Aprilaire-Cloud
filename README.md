# Aprilaire (Cloud) — Home Assistant integration

Bring legacy Wi-Fi Aprilaire thermostats — like the **8920W** — into Home
Assistant. These older models have **no local API** and only work through
Aprilaire's cloud, so this integration talks to the same backend the Aprilaire
mobile app uses.

> **Have a newer thermostat?** If yours is an Aprilaire *Home Automation*
> (8800-series) or *Zone Control* (6000-series) model, use the **built-in**
> [`aprilaire`](https://www.home-assistant.io/integrations/aprilaire/)
> integration instead — it talks to the thermostat locally and is faster and more
> reliable. This project exists only for the older cloud-only models the local
> integration cannot reach.

## Features

- **Full thermostat control** — current temperature and humidity, heat / cool /
  auto / off modes, single or dual (heat + cool) setpoints, fan mode
  (auto / on / circulate), and live status (heating / cooling / fan / idle).
- **Humidifier control** — if your system has a whole-home humidifier, turn it on
  or off and set its 1–7 level.
- **Sensors** — indoor temperature and humidity, outdoor temperature (if your
  thermostat has an outdoor sensor), and Wi-Fi signal.
- **Automatic history & statistics** — every sensor is tagged so Home Assistant's
  **History** and long-term **Statistics** dashboards chart your temperature and
  humidity over time with no extra setup.
- **Equipment-running sensors** — separate on/off binary sensors for the fan,
  heating, cooling, and humidifier, so each piece of equipment gets its own
  history and runtime, and drives automations directly.

## Installation

**HACS (recommended):**
1. In HACS, open the ⋮ menu → *Custom repositories* and add this repository with
   category *Integration*.
2. Install **Aprilaire (Cloud)**, then restart Home Assistant.

**Manual:**
Copy `custom_components/aprilaire_cloud` into your Home Assistant
`config/custom_components/` directory and restart.

## Setup

Go to *Settings → Devices & Services → Add Integration*, search for
**Aprilaire (Cloud)**, and sign in with the same email and password you use in
the Aprilaire mobile app. Thermostats on your account are discovered
automatically; if you have more than one, you'll be asked which to add.

## Good to know

- **Small delay on changes.** The thermostat checks in with the cloud on its own
  schedule, so a setpoint or mode change can take ~10–20 s to physically take
  effect. Home Assistant shows your change immediately and confirms it on the
  next check-in.
- **History comes from Home Assistant.** Aprilaire's cloud keeps no server-side
  history for temperature, humidity, or fan state, so this integration lets Home
  Assistant's own recorder build the charts from its regular polls — exactly what
  the History and Statistics dashboards are designed for.
- **Cloud-only.** If Aprilaire's servers or your internet connection are down,
  the thermostat is unreachable from Home Assistant.
- **Tested hardware.** Developed and verified against the **8920W**. Other
  cloud-only Aprilaire Wi-Fi thermostats on the same app backend are likely to
  work, but haven't been confirmed — reports welcome.
- **Unofficial.** This is an independent project, not affiliated with or endorsed
  by Aprilaire. Aprilaire was not involved in its creation, and it relies on an
  undocumented API that can change without notice.

## Contributing & internals

Building, testing, the local dev box, and how the cloud API was reverse-engineered
are documented in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md). Test details live
in [`tests/README.md`](tests/README.md), release history in
[`CHANGELOG.md`](CHANGELOG.md), and HACS publishing notes in
[`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## License

See [LICENSE](LICENSE).
