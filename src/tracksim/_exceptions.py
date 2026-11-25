"""Exceptions raised by the TrackSim client."""

from __future__ import annotations


class TrackSimError(Exception):
    """Base exception for every error raised by this package."""


class NetworkError(TrackSimError):
    """The TrackSim API could not be reached."""


class APIError(TrackSimError):
    """The TrackSim API returned an unsuccessful or unexpected response.

    ``message`` is the API's error string where one was returned
    (for example ``"driver_does_not_exist"``).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(APIError):
    """HTTP 401: the API key is missing or invalid."""


class PermissionDeniedError(APIError):
    """HTTP 403: the request is not allowed.

    Some endpoints also use 403 for an invalid API key, an invalid parameter
    or a resource belonging to another company, so check ``message``.
    """


class NotFoundError(APIError):
    """HTTP 404: the requested resource does not exist."""


class RateLimitError(APIError):
    """HTTP 429: too many requests. Wait before retrying."""
