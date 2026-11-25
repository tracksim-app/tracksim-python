"""TrackSim API client."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar, get_args
from urllib.parse import quote

import requests

from ._exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from ._models import Company, Driver, JobRoute, JobType, MapLink, MapRoute, MapRouteDetails
from ._version import __version__

DEFAULT_BASE_URL = "https://api.tracksim.app"

_ERRORS: dict[int, type[APIError]] = {
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}

_T = TypeVar("_T")


class TrackSim:
    """A client for the TrackSim API.

    Args:
        api_key: API key from the API tab of https://tracksim.app/integrations.
        timeout: Maximum number of seconds to wait for an API response.
        base_url: API root, without a version. Normally left unchanged.
        session: An existing ``requests.Session`` to send requests with.
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        base_url: str = DEFAULT_BASE_URL,
        session: requests.Session | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key must be a non-empty string")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._owns_session = session is None
        self._session.headers.update(
            {
                "Authorization": f"Api-Key {api_key.strip()}",
                "Accept": "application/json",
                "User-Agent": f"tracksim-python/{__version__}",
            }
        )

    # --- Company --------------------------------------------------------------

    def me(self) -> Company:
        """Return the company linked to the API key."""
        return self._parse(self._request("GET", "/v1/me"), Company._from_api)

    # --- Drivers --------------------------------------------------------------

    def add_driver(self, steam_id: str | int) -> Driver:
        """Add a Steam user to the company and return the new driver.

        Raises ``APIError`` with a message such as ``steam_profile_private``,
        ``resource_already_exists``, ``driver_no_compatible_games`` or
        ``max_driver_limit_reached``.
        """
        data = self._request("POST", "/v1/drivers/add", json={"steam_id": _id(steam_id)})
        return self._parse(data, Driver._from_api)

    def remove_driver(self, steam_id: str | int) -> None:
        """Remove a driver from the company.

        Raises ``APIError`` with the message ``driver_does_not_exist`` if the
        driver is not in the company.
        """
        self._request(
            "DELETE",
            "/v1/drivers/remove",
            expect_json=False,
            json={"steam_id": _id(steam_id)},
        )

    def get_driver(self, steam_id: str | int) -> Driver:
        """Return a driver in the company."""
        data = self._request("GET", f"/v3/drivers/{_path(steam_id)}/details")
        return self._parse(data, Driver._from_api)

    def manage_driver(
        self,
        steam_id: str | int,
        *,
        eut2_job_logging: bool | None = None,
        eut2_live_tracking: bool | None = None,
        eut2_coach_job_logging: bool | None = None,
        eut2_coach_live_tracking: bool | None = None,
        ats_job_logging: bool | None = None,
        ats_live_tracking: bool | None = None,
        ats_car_job_logging: bool | None = None,
        ats_car_live_tracking: bool | None = None,
    ) -> Driver:
        """Change a driver's job logging and live tracking settings.

        Only the settings you pass are sent; the rest are left unchanged.
        ``eut2_*`` and ``ats_*`` refer to trucks.
        """
        requested = {
            "eut2_job_logging": eut2_job_logging,
            "eut2_live_tracking": eut2_live_tracking,
            "eut2_coach_job_logging": eut2_coach_job_logging,
            "eut2_coach_live_tracking": eut2_coach_live_tracking,
            "ats_job_logging": ats_job_logging,
            "ats_live_tracking": ats_live_tracking,
            "ats_car_job_logging": ats_car_job_logging,
            "ats_car_live_tracking": ats_car_live_tracking,
        }
        settings = {key: value for key, value in requested.items() if value is not None}
        if not settings:
            raise ValueError("pass at least one setting to change")
        if any(not isinstance(value, bool) for value in settings.values()):
            raise TypeError("driver settings must be booleans")
        data = self._request("PATCH", f"/v3/drivers/{_path(steam_id)}/manage", json=settings)
        return self._parse(data, Driver._from_api)

    # --- Jobs -----------------------------------------------------------------

    def get_job_route(self, job_id: str | int, job_type: JobType) -> JobRoute:
        """Return the recorded coordinates of a job, from start to finish.

        Args:
            job_id: The job ID.
            job_type: ``"truck"``, ``"car"`` or ``"bus"``. Bus routes return
                ``BusRoutePoint`` items with passenger comfort telemetry.
        """
        if job_type not in get_args(JobType):
            raise ValueError("job_type must be 'truck', 'car' or 'bus'")
        data = self._request(
            "GET", f"/v2/jobs/{_path(job_id)}/route", params={"job_type": job_type}
        )
        return self._parse(data, lambda items: JobRoute._from_api(items, job_type), list)

    # --- Maps (requires the Route Planner) -----------------------------------

    def create_map_link(self) -> MapLink:
        """Create a one-time link for planning a new route. Expires after 24 hours."""
        return self._parse(self._request("POST", "/v3/maps/create"), MapLink._from_api)

    def create_map_edit_link(self, route_id: str) -> MapLink:
        """Create a one-time link for editing a route. Expires after 24 hours."""
        data = self._request("PATCH", f"/v3/maps/{_path(route_id)}/edit")
        return self._parse(data, MapLink._from_api)

    def list_map_routes(self) -> list[MapRoute]:
        """Return every saved route in the company (without waypoints)."""
        data = self._request("GET", "/v3/maps/routes")
        if not isinstance(data, list):
            raise APIError("TrackSim returned an unexpected response shape")
        return [self._parse(item, MapRoute._from_api) for item in data]

    def get_map_route(self, route_id: str) -> MapRouteDetails:
        """Return a saved route, including its waypoints."""
        data = self._request("GET", f"/v3/maps/{_path(route_id)}/route")
        return self._parse(data, MapRouteDetails._from_api)

    def delete_map_route(self, route_id: str) -> None:
        """Delete a saved route."""
        self._request("DELETE", f"/v3/maps/{_path(route_id)}/route")

    # --- Lifecycle ------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP session, if this client created it."""
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> TrackSim:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # --- Internals ------------------------------------------------------------

    def _request(self, method: str, path: str, *, expect_json: bool = True, **kwargs: Any) -> Any:
        try:
            response = self._session.request(
                method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            raise NetworkError(f"Could not connect to the TrackSim API: {exc}") from exc

        if not response.ok:
            raise _ERRORS.get(response.status_code, APIError)(
                _error_message(response),
                status_code=response.status_code,
                response_body=response.text,
            )

        if not expect_json:
            return None
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise APIError(
                "TrackSim returned a response that was not valid JSON",
                status_code=response.status_code,
                response_body=response.text,
            ) from exc

    @staticmethod
    def _parse(data: Any, parser: Callable[[Any], _T], kind: type = Mapping) -> _T:
        if not isinstance(data, kind):
            raise APIError("TrackSim returned an unexpected response shape")
        try:
            return parser(data)
        except (ValueError, TypeError) as exc:
            raise APIError(f"TrackSim returned an unexpected response: {exc}") from exc


def _id(value: str | int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("identifier must be a string or integer")
    identifier = str(value).strip()
    if not identifier:
        raise ValueError("identifier must not be empty")
    return identifier


def _path(value: str | int) -> str:
    return quote(_id(value), safe="")


def _error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except requests.exceptions.JSONDecodeError:
        body = None
    if isinstance(body, Mapping):
        for key in ("error", "message", "detail", "code"):
            value = body.get(key)
            if isinstance(value, str) and value:
                return value
    return f"TrackSim API request failed with status {response.status_code}"
