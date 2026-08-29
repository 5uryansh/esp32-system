"""Pydantic response models."""

from pydantic import BaseModel


class Weather(BaseModel):
    """Compact weather payload for the ESP32."""

    temperature: float  # Celsius
    humidity: int  # percent
    rain_probability: int  # percent
    wind_speed: float  # km/h
    weather: str  # human-readable description


class Usage(BaseModel):
    """Compact Claude Code quota payload for the ESP32."""

    session_pct: int  # percent of the current 5-hour session window used
    session_reset: str  # e.g. "Aug 29, 8:40am (UTC)"
    week_pct: int  # percent of the weekly all-models allowance used
    week_reset: str


class Health(BaseModel):
    status: str
