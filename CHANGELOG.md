# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-25

### Added

- Route planner endpoints: `create_map_link`, `create_map_edit_link`, `list_map_routes`,
  `get_map_route` and `delete_map_route`.
- `verify_webhook_signature` for checking the `tracksim-signature` header.
- Bus job routes, returned as `BusRoutePoint` with passenger comfort telemetry.
- Coach (ETS2) and car (ATS) tracking settings in `manage_driver` and `Driver.settings`.
- `PermissionDeniedError` (403), `NotFoundError` (404) and `RateLimitError` (429).
- Python 3.14 support.

### Changed

- **Breaking:** driver endpoints use API v3. `Driver.settings` is now nested by vehicle,
  for example `settings.eut2.truck.live_tracking`.
- **Breaking:** `get_job_route` uses API v2 and needs a `job_type` (`"truck"`, `"car"` or
  `"bus"`).
- **Breaking:** `manage_driver` arguments are optional; only the settings you pass are sent.
- **Breaking:** `AuthenticationError` is raised for 401 only; 403 raises
  `PermissionDeniedError`.
- **Breaking:** `base_url` no longer includes the API version
  (default `https://api.tracksim.app`).

### Removed

- **Breaking:** Python 3.9 support (end of life).
- `GameSettings`, replaced by `TrackingSettings`, `EUT2Settings` and `ATSSettings`.

## [0.2.0]

- Company details, adding, removing and managing drivers, driver details and job routes.

[1.0.0]: https://github.com/tracksim-app/tracksim-python/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/tracksim-app/tracksim-python/releases/tag/v0.2.0
