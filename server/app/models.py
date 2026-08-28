"""Pydantic response models."""

from pydantic import BaseModel


class Weather(BaseModel):
    """Compact weather payload for the ESP32."""

    temperature: float  # Celsius
    humidity: int  # percent
    rain_probability: int  # percent
    wind_speed: float  # km/h
    weather: str  # human-readable description


class Health(BaseModel):
    status: str
