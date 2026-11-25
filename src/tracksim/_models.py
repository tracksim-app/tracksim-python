"""Typed response models returned by the TrackSim client."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast, overload

Game = Literal["eut2", "ats"]
JobType = Literal["truck", "car", "bus"]


def _pretty(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _get(
    data: Mapping[str, Any],
    key: str,
    kind: type | tuple[type, ...],
    label: str,
    *,
    nullable: bool = False,
) -> Any:
    value = data.get(key)
    if value is None and nullable:
        return None
    # bool is a subclass of int, so reject it unless a bool was asked for.
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is not bool):
        raise ValueError(f"{key} must be {label}")
    return value


def _string(data: Mapping[str, Any], key: str, *, nullable: bool = False) -> Any:
    return _get(data, key, str, "a string", nullable=nullable)


def _integer(data: Mapping[str, Any], key: str) -> int:
    return cast(int, _get(data, key, int, "an integer"))


def _number(data: Mapping[str, Any], key: str) -> float:
    return float(_get(data, key, (int, float), "a number"))


def _boolean(data: Mapping[str, Any], key: str) -> bool:
    return cast(bool, _get(data, key, bool, "a boolean"))


def _mapping(data: Mapping[str, Any], key: str, *, nullable: bool = False) -> Any:
    return _get(data, key, Mapping, "an object", nullable=nullable)


class _Model:
    """Shared behaviour: ``to_dict()`` and pretty JSON when printed."""

    __slots__ = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the model as a JSON-compatible dictionary."""
        return cast("dict[str, Any]", dataclasses.asdict(self))  # type: ignore[call-overload]

    def __str__(self) -> str:
        return _pretty(self.to_dict())


# --- Company -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiscordRPC(_Model):
    """Discord Rich Presence application IDs for supported games."""

    eut2_app_id: str
    ats_app_id: str

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> DiscordRPC:
        return cls(_string(data, "eut2_app_id"), _string(data, "ats_app_id"))


@dataclass(frozen=True, slots=True)
class DriverCount(_Model):
    """Current and maximum company driver counts."""

    current: int
    max: int

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> DriverCount:
        return cls(_integer(data, "current"), _integer(data, "max"))


@dataclass(frozen=True, slots=True)
class Company(_Model):
    """The company linked to a TrackSim API key."""

    id: int
    name: str
    logo_url: str
    discord_rpc: DiscordRPC
    driver_count: DriverCount

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> Company:
        return cls(
            id=_integer(data, "id"),
            name=_string(data, "name"),
            logo_url=_string(data, "logo_url"),
            discord_rpc=DiscordRPC._from_api(_mapping(data, "discord_rpc")),
            driver_count=DriverCount._from_api(_mapping(data, "driver_count")),
        )


# --- Drivers -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DriverClientVersion(_Model):
    """Installed TrackSim client version details. All fields are None when not installed."""

    version: str | None
    branch: str | None
    platform: str | None

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> DriverClientVersion:
        return cls(
            _string(data, "version", nullable=True),
            _string(data, "branch", nullable=True),
            _string(data, "platform", nullable=True),
        )


@dataclass(frozen=True, slots=True)
class DriverClient(_Model):
    """A driver's TrackSim client installation state."""

    is_installed: bool
    version: DriverClientVersion | None

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> DriverClient:
        version = _mapping(data, "version", nullable=True)
        return cls(
            is_installed=_boolean(data, "is_installed"),
            version=DriverClientVersion._from_api(version) if version is not None else None,
        )


@dataclass(frozen=True, slots=True)
class TrackingSettings(_Model):
    """Job logging and live tracking flags for one game and vehicle type."""

    job_logging: bool
    live_tracking: bool

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> TrackingSettings:
        return cls(_boolean(data, "job_logging"), _boolean(data, "live_tracking"))


@dataclass(frozen=True, slots=True)
class EUT2Settings(_Model):
    """Euro Truck Simulator 2 tracking settings."""

    truck: TrackingSettings
    coach: TrackingSettings

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> EUT2Settings:
        return cls(
            TrackingSettings._from_api(_mapping(data, "truck")),
            TrackingSettings._from_api(_mapping(data, "coach")),
        )


@dataclass(frozen=True, slots=True)
class ATSSettings(_Model):
    """American Truck Simulator tracking settings."""

    truck: TrackingSettings
    car: TrackingSettings

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> ATSSettings:
        return cls(
            TrackingSettings._from_api(_mapping(data, "truck")),
            TrackingSettings._from_api(_mapping(data, "car")),
        )


@dataclass(frozen=True, slots=True)
class DriverSettings(_Model):
    """A driver's tracking settings for every supported game."""

    eut2: EUT2Settings
    ats: ATSSettings

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> DriverSettings:
        return cls(
            EUT2Settings._from_api(_mapping(data, "eut2")),
            ATSSettings._from_api(_mapping(data, "ats")),
        )


@dataclass(frozen=True, slots=True)
class Driver(_Model):
    """A driver in a TrackSim company."""

    id: int
    steam_id: str
    username: str
    profile_photo_url: str
    client: DriverClient
    settings: DriverSettings | None  # None for add_driver, which omits settings.
    is_banned: bool
    last_active: str | None

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> Driver:
        settings = _mapping(data, "settings", nullable=True)
        return cls(
            id=_integer(data, "id"),
            steam_id=_string(data, "steam_id"),
            username=_string(data, "username"),
            profile_photo_url=_string(data, "profile_photo_url"),
            client=DriverClient._from_api(_mapping(data, "client")),
            settings=DriverSettings._from_api(settings) if settings is not None else None,
            is_banned=_boolean(data, "is_banned"),
            last_active=_string(data, "last_active", nullable=True),
        )


# --- Job routes --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RoutePoint(_Model):
    """One recorded coordinate of a truck or car job."""

    x: float
    z: float
    time: int

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> RoutePoint:
        return cls(_number(data, "x"), _number(data, "z"), _integer(data, "time"))


@dataclass(frozen=True, slots=True)
class BusRoutePoint(RoutePoint):
    """One recorded coordinate of a bus job, with passenger comfort telemetry."""

    speed_kmh: float
    satisfaction: float
    peak_lateral_g: float
    peak_braking_g: float
    peak_acceleration_g: float
    peak_vertical_g: float

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> BusRoutePoint:
        return cls(
            x=_number(data, "x"),
            z=_number(data, "z"),
            time=_integer(data, "time"),
            speed_kmh=_number(data, "speed_kmh"),
            satisfaction=_number(data, "satisfaction"),
            peak_lateral_g=_number(data, "peak_lateral_g"),
            peak_braking_g=_number(data, "peak_braking_g"),
            peak_acceleration_g=_number(data, "peak_acceleration_g"),
            peak_vertical_g=_number(data, "peak_vertical_g"),
        )


@dataclass(frozen=True, slots=True)
class JobRoute:
    """The ordered coordinates of a job, from start to finish."""

    points: tuple[RoutePoint, ...]

    @classmethod
    def _from_api(cls, data: list[Any], job_type: JobType) -> JobRoute:
        point_type = BusRoutePoint if job_type == "bus" else RoutePoint
        points = []
        for index, item in enumerate(data):
            if not isinstance(item, Mapping):
                raise ValueError(f"route point {index} must be an object")
            points.append(point_type._from_api(item))
        return cls(tuple(points))

    def __iter__(self) -> Iterator[RoutePoint]:
        return iter(self.points)

    def __len__(self) -> int:
        return len(self.points)

    @overload
    def __getitem__(self, index: int) -> RoutePoint: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[RoutePoint, ...]: ...

    def __getitem__(self, index: int | slice) -> RoutePoint | tuple[RoutePoint, ...]:
        return self.points[index]

    def to_list(self) -> list[dict[str, Any]]:
        """Return the route as a JSON-compatible list."""
        return [point.to_dict() for point in self.points]

    def __str__(self) -> str:
        return _pretty(self.to_list())


# --- Maps --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MapLink(_Model):
    """A one-time route planner link. Treat both fields as secrets."""

    full_url: str = field(repr=False)
    flag: str = field(repr=False)

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> MapLink:
        return cls(_string(data, "full_url"), _string(data, "flag"))


@dataclass(frozen=True, slots=True)
class MapRoute(_Model):
    """A saved route planner route (without waypoints)."""

    id: str
    game: Game
    map: str
    name: str | None
    convoy: bool
    created_at: str
    updated_at: str

    @classmethod
    def _fields(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": _string(data, "id"),
            "game": _string(data, "game"),
            "map": _string(data, "map"),
            "name": _string(data, "name", nullable=True),
            "convoy": _boolean(data, "convoy"),
            "created_at": _string(data, "created_at"),
            "updated_at": _string(data, "updated_at"),
        }

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> MapRoute:
        return cls(**cls._fields(data))


@dataclass(frozen=True, slots=True)
class CustomDomain(_Model):
    """A company's verified custom map domain."""

    domain: str | None

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> CustomDomain:
        return cls(_string(data, "domain", nullable=True))


@dataclass(frozen=True, slots=True)
class Tenant(_Model):
    """The company that owns a map route."""

    id: int
    slug: str
    name: str
    custom_domain: CustomDomain | None

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> Tenant:
        domain = _mapping(data, "custom_domain", nullable=True)
        return cls(
            id=_integer(data, "id"),
            slug=_string(data, "slug"),
            name=_string(data, "name"),
            custom_domain=CustomDomain._from_api(domain) if domain is not None else None,
        )


@dataclass(frozen=True, slots=True)
class MapRouteDetails(MapRoute):
    """A saved route planner route, including waypoints and owner."""

    # shortcut: waypoint shape is undocumented, so it is passed through as raw JSON.
    waypoints: list[Any]
    tenant: Tenant

    @classmethod
    def _from_api(cls, data: Mapping[str, Any]) -> MapRouteDetails:
        waypoints = _get(data, "waypoints", list, "an array")
        return cls(
            **cls._fields(data),
            waypoints=waypoints,
            tenant=Tenant._from_api(_mapping(data, "tenant")),
        )
