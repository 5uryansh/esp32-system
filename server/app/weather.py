"""Open-Meteo client: request, parsing and WMO weather-code conversion."""

import logging

import httpx

from . import config
from .models import Weather

logger = logging.getLogger(__name__)

# WMO weather interpretation codes used by Open-Meteo.
WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherUnavailable(Exception):
    """Raised when Open-Meteo cannot be reached or its response is unusable."""


def describe(code: int) -> str:
    """Convert a WMO weather code into a human-readable description."""
    return WMO_CODES.get(code, "Unknown")


PARAMS = {
    "latitude": config.WEATHER_LATITUDE,
    "longitude": config.WEATHER_LONGITUDE,
    "current": "temperature_2m,relative_humidity_2m,precipitation_probability,"
    "wind_speed_10m,weather_code",
    "temperature_unit": "celsius",
    "wind_speed_unit": "kmh",
    "timezone": "auto",
}


async def fetch_weather() -> Weather:
    """Fetch current weather from Open-Meteo and reduce it to our small payload."""
    try:
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
            response = await client.get(config.OPEN_METEO_URL, params=PARAMS)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Open-Meteo returned HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise WeatherUnavailable("upstream returned an error status") from exc
    except httpx.HTTPError as exc:
        logger.error("Open-Meteo request failed: %s", exc)
        raise WeatherUnavailable("upstream request failed") from exc
    except ValueError as exc:
        logger.error("Open-Meteo returned a non-JSON body: %s", exc)
        raise WeatherUnavailable("upstream returned invalid JSON") from exc

    return _parse(payload)


def _parse(payload: dict) -> Weather:
    current = payload.get("current")
    if not isinstance(current, dict):
        logger.error("Open-Meteo response missing 'current' block: %s", payload)
        raise WeatherUnavailable("upstream response missing current weather")

    try:
        return Weather(
            temperature=round(float(current["temperature_2m"]), 1),
            humidity=round(float(current["relative_humidity_2m"])),
            # precipitation_probability can be null when the model has no value.
            rain_probability=round(float(current.get("precipitation_probability") or 0)),
            wind_speed=round(float(current["wind_speed_10m"]), 1),
            weather=describe(int(current["weather_code"])),
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.error("Could not parse Open-Meteo current weather %s: %s", current, exc)
        raise WeatherUnavailable("upstream response could not be parsed") from exc
