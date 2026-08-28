"""FastAPI application: routes and authentication."""

import logging
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, status

from . import config
from .models import Health, Weather
from .weather import WeatherUnavailable, fetch_weather

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ESP32 Weather Service")


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """Reject requests that do not carry the correct X-API-Key header."""
    if not secrets.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


@app.get("/health", response_model=Health)
async def health() -> Health:
    return Health(status="ok")


@app.get("/api/weather", response_model=Weather, dependencies=[Depends(require_api_key)])
async def weather() -> Weather:
    try:
        return await fetch_weather()
    except WeatherUnavailable:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather data unavailable",
        ) from None
