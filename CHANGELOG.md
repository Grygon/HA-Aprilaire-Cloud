# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
