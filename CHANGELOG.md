# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Humidifier controls: a **switch** (on/off) and a **number** for the 1–7 dial
  level (Aprilaire's `autoModeSetpoint`). Setting a level turns the humidifier on
  at that level; the device reports level 0 while off.

### Changed
- The humidifier running-state sensor is now a normal sensor (**Humidifier
  status**) instead of a diagnostic entity, so it appears alongside the other
  sensors.
- Polls are now aligned to wall-clock multiples of the scan interval (e.g. on the
  minute at `:00` for the default 60 s interval) instead of drifting to an
  arbitrary offset.

## [0.1.0] - 2026-08-22

### Added
- Initial release for cloud-only Wi-Fi Aprilaire thermostats (verified against the
  **8920W**).
- Climate entity: current temperature and humidity; heat / cool / auto / off modes;
  single and dual (heat + cool) setpoints; fan modes (auto / on / circulate); live
  HVAC action (heating / cooling / fan / idle).
- Sensors: indoor temperature, indoor humidity, outdoor temperature (when present),
  Wi-Fi signal (diagnostic), and humidifier status.
- Binary sensor: fan running.
- Config flow with email/password login, multi-device discovery/picker, and reauth.
- Optimistic writes with a delayed reconcile so UI changes appear immediately and
  are confirmed on the device's next cloud check-in.
- Local dev box (`devbox/`) and a 30-test unit + HA-harness suite.

[Unreleased]: https://github.com/Grygon/HA-Aprilaire-Cloud/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Grygon/HA-Aprilaire-Cloud/releases/tag/v0.1.0
