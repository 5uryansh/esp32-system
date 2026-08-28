"""Environment configuration."""

import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _required_float(name: str) -> float:
    value = _required(name)
    try:
        return float(value)
    except ValueError:
        raise RuntimeError(f"Environment variable {name} must be a number") from None


API_KEY: str = _required("API_KEY")
WEATHER_LATITUDE: float = _required_float("WEATHER_LATITUDE")
WEATHER_LONGITUDE: float = _required_float("WEATHER_LONGITUDE")

# Open-Meteo forecast endpoint (no API key required).
OPEN_METEO_URL: str = "https://api.open-meteo.com/v1/forecast"

# Seconds to wait for Open-Meteo before giving up.
HTTP_TIMEOUT: float = 10.0
