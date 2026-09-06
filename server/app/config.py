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

SPOTIFY_CLIENT_ID  = _required("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET  = _required("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-recently-played"
SPOTIFY_REFRESH_TOKEN = _required("SPOTIFY_REFRESH_TOKEN")

# Album art is dithered to a square 1-bit bitmap for the e-ink panel. Rows are
# packed 8 pixels per byte, so the size must be a multiple of 8.
SPOTIFY_ART_SIZE: int = int(os.getenv("SPOTIFY_ART_SIZE", "").strip() or 200)
if SPOTIFY_ART_SIZE % 8:
    raise RuntimeError("SPOTIFY_ART_SIZE must be a multiple of 8")
