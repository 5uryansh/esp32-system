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

# `claude -p "/usage"` runs a real Claude Code session: slow, and it counts
# against the quota it reports. So keep it on the cheap model and reuse the
# reading for a while.
CLAUDE_BIN: str = "claude"
CLAUDE_USAGE_MODEL: str = "claude-haiku-4-5-20251001"
CLAUDE_USAGE_TIMEOUT: float = 60.0
CLAUDE_USAGE_TTL: float = 300.0
