"""Spotify: refreshes the access token and reads the currently playing track."""

import asyncio
import base64
import logging
import time

import httpx

from . import config
from .models import NowPlaying

logger = logging.getLogger(__name__)

TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYED_URL = "https://api.spotify.com/v1/me/player/recently-played?limit=1"


class SpotifyUnavailable(Exception):
    """Raised when Spotify cannot be reached or its response is unusable."""


# Access tokens last an hour; keep one in memory and refresh when it expires.
_access_token: str | None = None
_expires_at: float = 0.0
_lock = asyncio.Lock()


def _basic_auth() -> str:
    pair = f"{config.SPOTIFY_CLIENT_ID}:{config.SPOTIFY_CLIENT_SECRET}"
    return base64.b64encode(pair.encode()).decode()


async def _refresh(client: httpx.AsyncClient) -> str:
    """Exchange the long-lived refresh token for a fresh access token."""
    global _access_token, _expires_at

    try:
        response = await client.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {_basic_auth()}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": config.SPOTIFY_REFRESH_TOKEN,
            },
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Spotify token refresh failed with HTTP %s: %s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise SpotifyUnavailable("could not refresh access token") from exc
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Spotify token refresh failed: %s", exc)
        raise SpotifyUnavailable("could not refresh access token") from exc

    token = payload.get("access_token")
    if not token:
        logger.error("Spotify token response had no access_token: %s", payload)
        raise SpotifyUnavailable("token response missing access_token")

    # Expire a minute early so a request never races the deadline.
    _access_token = token
    _expires_at = time.monotonic() + float(payload.get("expires_in", 3600)) - 60
    return token


async def _token(client: httpx.AsyncClient, force: bool = False) -> str:
    async with _lock:
        if force or _access_token is None or time.monotonic() >= _expires_at:
            return await _refresh(client)
        return _access_token


async def fetch_now_playing() -> NowPlaying:
    """Return what is playing, falling back to the last played track."""
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT) as client:
        response = await _get(client, NOW_PLAYING_URL)

        # 204 means the account is connected but nothing is playing at all.
        if response.status_code == 204 or not response.content:
            return await _last_played(client)

        current = _parse(_json(response))
        # Ads and podcasts arrive with no track item; history is more useful.
        if current.track is None:
            return await _last_played(client)
        return current


async def _last_played(client: httpx.AsyncClient) -> NowPlaying:
    """Return the most recently finished track, or an empty payload."""
    response = await _get(client, RECENTLY_PLAYED_URL, allow_403=True)
    if response.status_code == 403:
        logger.error(
            "Spotify rejected recently-played: the token lacks the "
            "user-read-recently-played scope. Re-run app.spotify_auth."
        )
        return NowPlaying(is_playing=False)

    items = _json(response).get("items") or []
    if not items:
        return NowPlaying(is_playing=False)

    entry = items[0]
    played = _parse({"is_playing": False, "item": entry.get("track")})
    # progress is meaningless for a finished track; report when it played instead.
    return played.model_copy(
        update={"progress": None, "played_at": entry.get("played_at")}
    )


async def _get(
    client: httpx.AsyncClient, url: str, allow_403: bool = False
) -> httpx.Response:
    """GET a Spotify endpoint, refreshing the access token once on a 401."""
    try:
        response = await client.get(
            url, headers={"Authorization": f"Bearer {await _token(client)}"}
        )
        # A token can be revoked before it expires; retry once with a new one.
        if response.status_code == 401:
            logger.info("Spotify returned 401, refreshing access token")
            token = await _token(client, force=True)
            response = await client.get(
                url, headers={"Authorization": f"Bearer {token}"}
            )
    except httpx.HTTPError as exc:
        logger.error("Spotify request failed: %s", exc)
        raise SpotifyUnavailable("upstream request failed") from exc

    if response.status_code in (200, 204) or (allow_403 and response.status_code == 403):
        return response

    logger.error(
        "Spotify returned HTTP %s for %s: %s",
        response.status_code,
        url,
        response.text[:500],
    )
    raise SpotifyUnavailable("upstream returned an error status")


def _json(response: httpx.Response) -> dict:
    try:
        return response.json()
    except ValueError as exc:
        logger.error("Spotify returned a non-JSON body: %s", exc)
        raise SpotifyUnavailable("upstream returned invalid JSON") from exc


def _parse(payload: dict) -> NowPlaying:
    item = payload.get("item")
    if not isinstance(item, dict):
        # Ads and podcast episodes come back without a track item.
        return NowPlaying(is_playing=bool(payload.get("is_playing")))


    artists = ", ".join(
        a["name"] for a in item.get("artists", []) if isinstance(a, dict) and a.get("name")
    )
    return NowPlaying(
        is_playing=bool(payload.get("is_playing")),
        track=item.get("name"),
        artist=artists or None,
        album=(item.get("album") or {}).get("name"),
        progress=round((payload.get("progress_ms") or 0) / 1000),
        duration=round((item.get("duration_ms") or 0) / 1000),
    )
