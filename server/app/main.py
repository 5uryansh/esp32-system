"""FastAPI application: routes and authentication."""

import logging
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status

from . import config
from .models import Health, NowPlaying, Usage, Weather
from .spotify import SpotifyUnavailable, fetch_art, fetch_now_playing
from .usage import UsageUnavailable, get_usage
from .weather import WeatherUnavailable, fetch_weather

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ESP32 Dashboard Service")


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


@app.get("/api/usage", response_model=Usage, dependencies=[Depends(require_api_key)])
async def usage() -> Usage:
    try:
        return await get_usage()
    except UsageUnavailable:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Usage data unavailable",
        ) from None


@app.get(
    "/api/spotify", response_model=NowPlaying, dependencies=[Depends(require_api_key)]
)
async def spotify() -> NowPlaying:
    try:
        return await fetch_now_playing()
    except SpotifyUnavailable:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Spotify data unavailable",
        ) from None


@app.get("/api/spotify/art", dependencies=[Depends(require_api_key)])
async def spotify_art() -> Response:
    """Album art as a packed 1-bit bitmap, ready to blit to an e-ink panel."""
    try:
        return Response(
            content=await fetch_art(), media_type="application/octet-stream"
        )
    except SpotifyUnavailable:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Album art unavailable",
        ) from None
