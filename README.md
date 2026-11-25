<p align="center">
  <a href="https://tracksim.app">
    <img src="https://tracksim-prod.s3.eu-west-2.amazonaws.com/public/logos/TrackSim-logo-full-color.png" alt="TrackSim" width="320">
  </a>
</p>

# TrackSim Python

[![PyPI](https://img.shields.io/pypi/v/TrackSim.svg)](https://pypi.org/project/TrackSim/)
[![Python versions](https://img.shields.io/pypi/pyversions/TrackSim.svg)](https://pypi.org/project/TrackSim/)
[![CI](https://github.com/tracksim-app/tracksim-python/actions/workflows/ci.yml/badge.svg)](https://github.com/tracksim-app/tracksim-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The official Python client for the [TrackSim API](https://docs.tracksim.app): manage your
VTC's drivers, read job routes, work with the route planner and verify webhooks, with
typed responses throughout.

## Installation

```bash
pip install TrackSim
```

Requires Python 3.10 or newer.

## Quick start

Generate an API key from the **API** tab of the
[integrations page](https://tracksim.app/integrations). Keep it secret: load it from an
environment variable or secrets manager rather than committing it.

```python
import os
from tracksim import TrackSim

with TrackSim(api_key=os.environ["TRACKSIM_API_KEY"]) as tracksim:
    company = tracksim.me()
    print(company.name, company.driver_count.current)
```

Every response is a typed, immutable object. Use dot notation for fields, `.to_dict()`
for plain JSON-compatible data, and `print()` for readable, indented JSON.

## Drivers

```python
driver = tracksim.add_driver("76561198171686422")
driver = tracksim.get_driver("76561198171686422")

print(driver.username)
print(driver.settings.eut2.truck.live_tracking)
print(driver.settings.ats.car.job_logging)

# Only the settings you pass are changed.
driver = tracksim.manage_driver(
    "76561198171686422",
    eut2_job_logging=True,  # ETS2 trucks
    eut2_live_tracking=True,
    eut2_coach_job_logging=True,  # ETS2 coaches
    ats_car_live_tracking=False,  # ATS cars
)

tracksim.remove_driver("76561198171686422")
```

## Job routes

`job_type` is `"truck"`, `"car"` or `"bus"`.

```python
route = tracksim.get_job_route(123, "truck")

for point in route:
    print(point.x, point.z, point.time)

bus_route = tracksim.get_job_route(456, "bus")
print(bus_route[0].speed_kmh, bus_route[0].satisfaction)
```

Route data rarely changes once a job is complete, so store it on your side if you need it
often.

## Route planner (maps)

Requires a TrackSim map and the Route Planner add-on. Limited to 60 requests a minute.

```python
link = tracksim.create_map_link()  # plan a new route
link = tracksim.create_map_edit_link(route_id)  # edit an existing one
print(link.full_url)  # one-time link, expires after 24 hours: treat it as a secret

for route in tracksim.list_map_routes():
    print(route.id, route.game, route.name)

route = tracksim.get_map_route(route_id)
print(route.waypoints, route.tenant.name)

tracksim.delete_map_route(route_id)
```

## Webhooks

Check the `tracksim-signature` header against the secret shown when you created the
webhook before trusting a payload. For example, with Flask:

```python
from flask import Flask, abort, request
from tracksim import verify_webhook_signature

app = Flask(__name__)


@app.post("/tracksim")
def tracksim_webhook():
    if not verify_webhook_signature(
        request.get_data(), request.headers.get("tracksim-signature"), WEBHOOK_SECRET
    ):
        abort(401)
    event = request.get_json()
    print(event["type"])
    return "", 204
```

## Errors

Every exception inherits from `TrackSimError`.

| Exception | When |
| --- | --- |
| `AuthenticationError` | 401: missing or invalid API key |
| `PermissionDeniedError` | 403: not allowed (some endpoints also use this for an invalid key or unknown resource) |
| `NotFoundError` | 404: resource not found |
| `RateLimitError` | 429: too many requests |
| `APIError` | any other error response, or a response the client did not expect |
| `NetworkError` | TrackSim could not be reached |

`APIError` and its subclasses carry `message` (the API's error code, such as
`max_driver_limit_reached`), `status_code` and `response_body`.

```python
from tracksim import APIError, NotFoundError

try:
    tracksim.add_driver("76561198171686422")
except APIError as error:
    if error.message == "steam_profile_private":
        print("Ask the driver to make their Steam profile public")
    else:
        raise
```

## Configuration

```python
TrackSim(
    api_key="...",
    timeout=30.0,  # seconds per request
    session=my_session,  # reuse your own requests.Session (proxies, retries, ...)
)
```

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). To
report a security issue, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Omnibyte Technologies Limited
