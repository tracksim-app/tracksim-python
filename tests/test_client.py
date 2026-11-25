from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from unittest.mock import Mock

import requests

from tracksim import (
    APIError,
    AuthenticationError,
    BusRoutePoint,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    TrackSim,
    verify_webhook_signature,
)

BASE = "https://api.tracksim.app"
STEAM_ID = "76561198171686422"
ROUTE_ID = "3f1c9a52-7d0e-4b8a-9c61-2e5f8d4b7a10"


def tracking(job_logging: bool, live_tracking: bool) -> dict[str, bool]:
    return {"job_logging": job_logging, "live_tracking": live_tracking}


COMPANY_DATA = {
    "id": 87,
    "name": "Nathan's VTC",
    "logo_url": "https://example.com/logo.png",
    "discord_rpc": {"eut2_app_id": "ets2-id", "ats_app_id": "ats-id"},
    "driver_count": {"current": 2, "max": 0},
}

DRIVER_DATA = {
    "id": 7489,
    "steam_id": STEAM_ID,
    "username": "Nathan7471",
    "profile_photo_url": "https://example.com/avatar.jpg",
    "client": {
        "is_installed": True,
        "version": {"version": "2.2.1", "branch": "production", "platform": "windows"},
    },
    "settings": {
        "eut2": {"truck": tracking(True, False), "coach": tracking(False, True)},
        "ats": {"truck": tracking(True, True), "car": tracking(False, False)},
    },
    "is_banned": False,
    "last_active": "2026-11-13T02:19:58.153Z",
}

MAP_ROUTE_DATA = {
    "id": ROUTE_ID,
    "game": "eut2",
    "map": "default",
    "name": "Convoy to Berlin",
    "convoy": True,
    "created_at": "2026-11-13T02:19:58.153Z",
    "updated_at": "2026-11-13T02:19:58.153Z",
}


def response(*, status: int = 200, json_data: object = None) -> Mock:
    result = Mock(spec=requests.Response)
    result.status_code = status
    result.ok = 200 <= status < 400
    result.text = json.dumps(json_data)
    result.json.return_value = json_data
    return result


class TrackSimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Mock(spec=requests.Session)
        self.session.headers = {}
        self.client = TrackSim(api_key=" TEST ", session=self.session)

    def reply(self, json_data: object = None, status: int = 200) -> None:
        self.session.request.return_value = response(status=status, json_data=json_data)

    def assert_called(self, method: str, path: str, **kwargs: object) -> None:
        self.session.request.assert_called_once_with(
            method, f"{BASE}{path}", timeout=30.0, **kwargs
        )

    # --- Company ---

    def test_me_authenticates_and_parses_company(self) -> None:
        self.reply(COMPANY_DATA)
        company = self.client.me()

        self.assertEqual(company.name, "Nathan's VTC")
        self.assertEqual(company.driver_count.current, 2)
        self.assertEqual(company.to_dict(), COMPANY_DATA)
        self.assertEqual(json.loads(str(company)), COMPANY_DATA)
        self.assertEqual(self.session.headers["Authorization"], "Api-Key TEST")
        self.assert_called("GET", "/v1/me")

    def test_unexpected_response_shape_raises_api_error(self) -> None:
        self.reply([])
        with self.assertRaises(APIError):
            self.client.me()

    def test_boolean_is_not_accepted_as_integer(self) -> None:
        self.reply({**COMPANY_DATA, "id": True})
        with self.assertRaises(APIError):
            self.client.me()

    # --- Drivers ---

    def test_add_driver(self) -> None:
        self.reply(DRIVER_DATA)
        driver = self.client.add_driver(int(STEAM_ID))

        self.assertEqual(driver.to_dict(), DRIVER_DATA)
        self.assert_called("POST", "/v1/drivers/add", json={"steam_id": STEAM_ID})

    def test_remove_driver(self) -> None:
        self.reply(None)
        self.assertIsNone(self.client.remove_driver(STEAM_ID))
        self.assert_called("DELETE", "/v1/drivers/remove", json={"steam_id": STEAM_ID})

    def test_get_driver_parses_v3_settings(self) -> None:
        self.reply(DRIVER_DATA)
        driver = self.client.get_driver(STEAM_ID)

        self.assertTrue(driver.settings.eut2.coach.live_tracking)
        self.assertFalse(driver.settings.ats.car.job_logging)
        self.assertEqual(driver.client.version.platform, "windows")
        self.assert_called("GET", f"/v3/drivers/{STEAM_ID}/details")

    def test_manage_driver_sends_only_given_settings(self) -> None:
        self.reply(DRIVER_DATA)
        self.client.manage_driver(STEAM_ID, eut2_coach_live_tracking=True, ats_job_logging=False)

        self.assert_called(
            "PATCH",
            f"/v3/drivers/{STEAM_ID}/manage",
            json={"eut2_coach_live_tracking": True, "ats_job_logging": False},
        )

    def test_manage_driver_validates_settings(self) -> None:
        with self.assertRaises(ValueError):
            self.client.manage_driver(STEAM_ID)
        with self.assertRaises(TypeError):
            self.client.manage_driver(STEAM_ID, ats_live_tracking=1)  # type: ignore[arg-type]
        self.session.request.assert_not_called()

    def test_path_identifiers_are_escaped(self) -> None:
        self.reply(DRIVER_DATA)
        self.client.get_driver("../me")
        self.assert_called("GET", "/v3/drivers/..%2Fme/details")

    # --- Job routes ---

    def test_get_job_route_truck(self) -> None:
        points = [{"x": -104770.3412, "z": -4.7508, "time": 1677627692}]
        self.reply(points)
        route = self.client.get_job_route(123, "truck")

        self.assertEqual(route[0].x, -104770.3412)
        self.assertEqual(route.to_list(), points)
        self.assert_called("GET", "/v2/jobs/123/route", params={"job_type": "truck"})

    def test_get_job_route_bus_includes_telemetry(self) -> None:
        point = {
            "x": -13514.82,
            "z": -6209.26,
            "time": 1794507262,
            "speed_kmh": 67.4,
            "satisfaction": 0.0004,
            "peak_lateral_g": 0.1,
            "peak_braking_g": 0.2,
            "peak_acceleration_g": 0.3,
            "peak_vertical_g": 0.4,
        }
        self.reply([point])
        route = self.client.get_job_route(5, "bus")

        self.assertIsInstance(route[0], BusRoutePoint)
        self.assertEqual(route.to_list(), [point])

    def test_get_job_route_rejects_unknown_job_type(self) -> None:
        with self.assertRaises(ValueError):
            self.client.get_job_route(5, "plane")  # type: ignore[arg-type]

    # --- Maps ---

    def test_create_map_link_hides_secrets_in_repr(self) -> None:
        self.reply({"full_url": "https://map.example?flags=secret", "flag": "secret"})
        link = self.client.create_map_link()

        self.assertEqual(link.flag, "secret")
        self.assertNotIn("secret", repr(link))
        self.assert_called("POST", "/v3/maps/create")

    def test_create_map_edit_link(self) -> None:
        self.reply({"full_url": "https://map.example?flags=x", "flag": "x"})
        self.client.create_map_edit_link(ROUTE_ID)
        self.assert_called("PATCH", f"/v3/maps/{ROUTE_ID}/edit")

    def test_list_map_routes(self) -> None:
        self.reply([MAP_ROUTE_DATA, {**MAP_ROUTE_DATA, "name": None}])
        routes = self.client.list_map_routes()

        self.assertEqual(routes[0].name, "Convoy to Berlin")
        self.assertIsNone(routes[1].name)
        self.assert_called("GET", "/v3/maps/routes")

    def test_get_map_route(self) -> None:
        data = {
            **MAP_ROUTE_DATA,
            "waypoints": [{"x": 1, "z": 2}],
            "tenant": {
                "id": 123,
                "slug": "my-vtc",
                "name": "My VTC",
                "custom_domain": {"domain": "map.myvtc.com"},
            },
        }
        self.reply(data)
        route = self.client.get_map_route(ROUTE_ID)

        self.assertEqual(route.tenant.custom_domain.domain, "map.myvtc.com")
        self.assertEqual(route.to_dict(), data)
        self.assert_called("GET", f"/v3/maps/{ROUTE_ID}/route")

    def test_delete_map_route(self) -> None:
        self.reply({"deleted": True})
        self.assertIsNone(self.client.delete_map_route(ROUTE_ID))
        self.assert_called("DELETE", f"/v3/maps/{ROUTE_ID}/route")

    # --- Errors ---

    def test_status_codes_map_to_exceptions(self) -> None:
        cases = {
            401: AuthenticationError,
            403: PermissionDeniedError,
            404: NotFoundError,
            429: RateLimitError,
            500: APIError,
        }
        for status, error_type in cases.items():
            with self.subTest(status=status):
                self.reply({"error": "Map not found"}, status=status)
                with self.assertRaises(error_type) as caught:
                    self.client.get_map_route(ROUTE_ID)
                self.assertEqual(caught.exception.message, "Map not found")
                self.assertEqual(caught.exception.status_code, status)

    def test_network_errors_are_wrapped(self) -> None:
        self.session.request.side_effect = requests.ConnectionError("offline")
        with self.assertRaises(NetworkError):
            self.client.me()

    def test_invalid_constructor_arguments(self) -> None:
        with self.assertRaises(ValueError):
            TrackSim(api_key="  ", session=self.session)
        with self.assertRaises(ValueError):
            TrackSim(api_key="KEY", timeout=0, session=self.session)


class WebhookTests(unittest.TestCase):
    SECRET = "whsec"
    BODY = {"object": "event", "type": "job.delivered", "data": {"id": 1, "is_late": False}}

    def sign(self, body: object) -> str:
        message = json.dumps(body).encode()
        return hmac.new(self.SECRET.encode(), message, hashlib.sha256).hexdigest()

    def test_valid_signature_for_raw_and_parsed_bodies(self) -> None:
        signature = self.sign(self.BODY)
        raw = json.dumps(self.BODY, separators=(",", ":")).encode()

        self.assertTrue(verify_webhook_signature(self.BODY, signature, self.SECRET))
        self.assertTrue(verify_webhook_signature(raw, signature, self.SECRET))

    def test_invalid_signatures_are_rejected(self) -> None:
        signature = self.sign(self.BODY)

        self.assertFalse(verify_webhook_signature(self.BODY, signature, "wrong"))
        self.assertFalse(
            verify_webhook_signature({**self.BODY, "type": "x"}, signature, self.SECRET)
        )
        self.assertFalse(verify_webhook_signature(self.BODY, None, self.SECRET))
        self.assertFalse(verify_webhook_signature(b"not json", signature, self.SECRET))


if __name__ == "__main__":
    unittest.main()
