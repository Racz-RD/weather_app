from datetime import datetime
from math import isfinite

import httpx
import streamlit as st


HIGH_TEMPERATURE_C = 38
STRONG_WIND_GUST_KMH = 70
HEAVY_RAINFALL_MM_PER_HOUR = 20
HIGH_PRECIPITATION_PROBABILITY = 70
WEATHER_EVENT_CODES = {
    65: "Heavy rain",
    67: "Heavy freezing rain",
    75: "Heavy snow",
    82: "Heavy rain showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}
WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}

CURRENT_FIELDS = {
    "time",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_gusts_10m",
    "precipitation",
    "weather_code",
}
HOURLY_FIELDS = {
    "time",
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "wind_gusts_10m",
    "weather_code",
}


def _validate_weather_payload(weather):
    if not isinstance(weather, dict):
        raise ValueError("Weather response must be an object")

    current = weather.get("current")
    hourly = weather.get("hourly")
    if not isinstance(current, dict) or not isinstance(hourly, dict):
        raise ValueError("Weather response is missing current or hourly data")

    missing_current = CURRENT_FIELDS - current.keys()
    missing_hourly = HOURLY_FIELDS - hourly.keys()
    if missing_current or missing_hourly:
        raise ValueError("Weather response is missing required fields")

    lengths = {len(hourly[field]) for field in HOURLY_FIELDS}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 7:
        raise ValueError("Weather response contains an incomplete forecast")

    numeric_fields = CURRENT_FIELDS - {"time", "weather_code"}
    for field in numeric_fields:
        if not isinstance(current[field], (int, float)) or not isfinite(current[field]):
            raise ValueError("Weather response contains invalid current data")

    return current, hourly


@st.cache_data(ttl=600, show_spinner=False)
def fetch_weather(location, coordinates):
    latitude, longitude = coordinates
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                "wind_gusts_10m,precipitation,weather_code"
            ),
            "hourly": (
                "temperature_2m,precipitation,precipitation_probability,"
                "wind_gusts_10m,weather_code"
            ),
            "forecast_days": 2,
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    weather = response.json()
    current, hourly = _validate_weather_payload(weather)
    current_time = datetime.fromisoformat(current["time"])
    # Current observations may fall between the hourly forecast timestamps.
    current_hour_index = min(
        range(len(hourly["time"])),
        key=lambda index: abs(
            datetime.fromisoformat(hourly["time"][index]) - current_time
        ),
    )
    # Exclude the current hour and inspect the six subsequent forecast hours.
    next_six_hours = slice(current_hour_index + 1, current_hour_index + 7)
    forecast = {
        key: values[next_six_hours]
        for key, values in hourly.items()
        if key != "time"
    }
    return {
        "Location": location,
        "Temperature (°C)": current["temperature_2m"],
        "Condition": WEATHER_CODE_DESCRIPTIONS.get(
            current["weather_code"], "Unknown"
        ),
        "Wind Speed (km/h)": current["wind_speed_10m"],
        "Wind Gusts (km/h)": current["wind_gusts_10m"],
        "Humidity (%)": current["relative_humidity_2m"],
        "Rainfall (mm)": current["precipitation"],
        "Next 6h Rain (mm)": sum(forecast["precipitation"]),
        "Next 6h Max Rain (mm/h)": max(forecast["precipitation"]),
        "Next 6h Max Rain Probability (%)": max(
            forecast["precipitation_probability"]
        ),
        "Next 6h Max Wind Gust (km/h)": max(forecast["wind_gusts_10m"]),
        "Next 6h Max Temperature (°C)": max(forecast["temperature_2m"]),
        "Next 6h Weather Codes": forecast["weather_code"],
        "Updated": current["time"],
    }


def get_weather_alerts(row):
    alerts = []
    if row["Next 6h Max Temperature (°C)"] >= HIGH_TEMPERATURE_C:
        alerts.append(
            f"High temperature possible: {row['Next 6h Max Temperature (°C)']}°C"
        )
    if row["Next 6h Max Wind Gust (km/h)"] >= STRONG_WIND_GUST_KMH:
        alerts.append(
            f"Strong wind gusts possible: {row['Next 6h Max Wind Gust (km/h)']} km/h"
        )
    if (
        row["Next 6h Max Rain (mm/h)"] >= HEAVY_RAINFALL_MM_PER_HOUR
        or row["Next 6h Max Rain Probability (%)"] >= HIGH_PRECIPITATION_PROBABILITY
    ):
        alerts.append(
            f"Rain likely in next 6 hours: up to {row['Next 6h Max Rain (mm/h)']} mm/hour "
            f"({row['Next 6h Max Rain Probability (%)']}% probability)"
        )
    event_names = sorted(
        {
            WEATHER_EVENT_CODES[code]
            for code in row["Next 6h Weather Codes"]
            if code in WEATHER_EVENT_CODES
        }
    )
    alerts.extend(f"{event} possible in next 6 hours" for event in event_names)
    return alerts
