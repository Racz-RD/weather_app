import unittest
from unittest.mock import patch

import weather_service


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class ErrorResponse:
    def raise_for_status(self):
        raise weather_service.httpx.HTTPStatusError(
            "upstream failure",
            request=weather_service.httpx.Request(
                "GET", "https://api.open-meteo.com/v1/forecast"
            ),
            response=weather_service.httpx.Response(503),
        )


def weather_payload():
    return {
        "current": {
            "time": "2026-09-09T22:30",
            "temperature_2m": 28,
            "relative_humidity_2m": 65,
            "wind_speed_10m": 20,
            "wind_gusts_10m": 35,
            "precipitation": 0,
            "weather_code": 2,
        },
        "hourly": {
            "time": [
                "2026-09-09T22:00",
                "2026-09-09T23:00",
                "2026-09-10T00:00",
                "2026-09-10T01:00",
                "2026-09-10T02:00",
                "2026-09-10T03:00",
                "2026-09-10T04:00",
                "2026-09-10T05:00",
            ],
            "temperature_2m": [28, 29, 30, 31, 32, 33, 34, 35],
            "precipitation": [0, 1, 2, 0, 3, 4, 5, 6],
            "precipitation_probability": [10, 20, 30, 40, 50, 60, 80, 90],
            "wind_gusts_10m": [35, 40, 50, 60, 65, 75, 80, 90],
            "weather_code": [2, 2, 61, 63, 95, 2, 2, 2],
        },
    }


class WeatherDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = weather_service

    def test_fetch_weather_uses_next_six_hours_after_current_hour(self):
        with patch.object(
            self.service.httpx, "get", return_value=FakeResponse(weather_payload())
        ) as mock_get:
            result = self.service.fetch_weather(
                "Test location", (44.8, 20.2)
            )

        mock_get.assert_called_once()
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://api.open-meteo.com/v1/forecast",
        )
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 10)
        self.assertEqual(result["Condition"], "Partly cloudy")
        self.assertEqual(result["Next 6h Rain (mm)"], 15)
        self.assertEqual(result["Next 6h Max Rain (mm/h)"], 5)
        self.assertEqual(result["Next 6h Max Rain Probability (%)"], 80)
        self.assertEqual(result["Next 6h Max Wind Gust (km/h)"], 80)
        self.assertEqual(result["Next 6h Max Temperature (°C)"], 34)
        self.assertEqual(result["Next 6h Weather Codes"], [2, 61, 63, 95, 2, 2])

    def test_get_weather_alerts_reports_next_six_hour_events(self):
        row = {
            "Next 6h Max Temperature (°C)": 38,
            "Next 6h Max Wind Gust (km/h)": 75,
            "Next 6h Max Rain (mm/h)": 5,
            "Next 6h Max Rain Probability (%)": 80,
            "Next 6h Weather Codes": [2, 95],
        }

        alerts = self.service.get_weather_alerts(row)

        self.assertIn("High temperature possible: 38°C", alerts)
        self.assertIn("Strong wind gusts possible: 75 km/h", alerts)
        self.assertIn(
            "Rain likely in next 6 hours: up to 5 mm/hour (80% probability)",
            alerts,
        )
        self.assertIn("Thunderstorm possible in next 6 hours", alerts)

    def test_fetch_weather_propagates_upstream_http_errors(self):
        with patch.object(self.service.httpx, "get", return_value=ErrorResponse()):
            with self.assertRaises(self.service.httpx.HTTPStatusError):
                self.service.fetch_weather("Test location", (44.8, 20.2))

    def test_fetch_weather_rejects_malformed_upstream_payload(self):
        malformed_payload = {"current": {"time": "2026-09-09T22:30"}}

        with patch.object(
            self.service.httpx,
            "get",
            return_value=FakeResponse(malformed_payload),
        ):
            with self.assertRaises(ValueError):
                self.service.fetch_weather("Test location", (44.8, 20.2))

    def test_get_weather_alerts_returns_no_alerts_below_thresholds(self):
        row = {
            "Next 6h Max Temperature (°C)": 25,
            "Next 6h Max Wind Gust (km/h)": 40,
            "Next 6h Max Rain (mm/h)": 1,
            "Next 6h Max Rain Probability (%)": 20,
            "Next 6h Weather Codes": [0, 2],
        }

        self.assertEqual(self.service.get_weather_alerts(row), [])


if __name__ == "__main__":
    unittest.main()
