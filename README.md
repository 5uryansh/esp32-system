# ESP32 Dashboard Service

A tiny FastAPI service that serves two small JSON payloads an ESP32 can parse
directly:

- **weather** — current conditions from [Open-Meteo](https://open-meteo.com/en/docs)
- **usage** — Claude Code quota, read by running `claude -p "/usage"` locally
- **spotify** — the currently playing track, or the last one played

The ESP32 never talks to the weather provider and never needs Claude
credentials — it only talks to this server.

## Environment variables

Copy `.env.example` to `.env` and fill it in:

| Variable | Description |
| --- | --- |
| `WEATHER_LATITUDE` | Latitude of the location to report |
| `WEATHER_LONGITUDE` | Longitude of the location to report |
| `API_KEY` | Secret that clients must send as `X-API-Key` |
| `SPOTIFY_CLIENT_ID` | From your Spotify app dashboard |
| `SPOTIFY_CLIENT_SECRET` | From your Spotify app dashboard |
| `SPOTIFY_REFRESH_TOKEN` | Printed by `python -m app.spotify_auth` (run once) |

`.env` is git-ignored and must never be committed.

Open-Meteo itself requires no API key.

## Install

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
cd server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Auth | Returns |
| --- | --- | --- | --- |
| `GET` | `/health` | none | liveness check |
| `GET` | `/api/weather` | `X-API-Key` | current conditions |
| `GET` | `/api/usage` | `X-API-Key` | Claude Code quota |
| `GET` | `/api/spotify` | `X-API-Key` | current or last played track |

Both protected endpoints return `401` if `X-API-Key` is missing or wrong, and
`502` if their data source fails. Errors are a plain `{"detail": "..."}` —
internal exceptions are logged server-side, never returned.

### `GET /health`

Unauthenticated.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

### `GET /api/weather`

Requires the `X-API-Key` header. A missing or wrong key returns `401`.

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/weather
```

```json
{
  "temperature": 28.4,
  "humidity": 61,
  "rain_probability": 20,
  "wind_speed": 12.0,
  "weather": "Partly cloudy"
}
```

| Field | Unit | Source |
| --- | --- | --- |
| `temperature` | °C | `current.temperature_2m` |
| `humidity` | % | `current.relative_humidity_2m` |
| `rain_probability` | % | `current.precipitation_probability` (`0` if null) |
| `wind_speed` | km/h | `current.wind_speed_10m` |
| `weather` | text | `current.weather_code`, mapped from WMO code to words |

The server asks Open-Meteo for Celsius and km/h directly, then keeps only these
five fields — the raw upstream response is never passed through. WMO codes are
mapped in `app/weather.py` (`0` Clear sky … `95` Thunderstorm); an unrecognised
code becomes `"Unknown"`.

If Open-Meteo is unreachable, times out (10s), or returns something unparseable,
the server responds `502` and logs the reason.

### `GET /api/usage`

Requires the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/usage
```

```json
{
  "session_pct": 15,
  "session_reset": "Aug 29, 8:40am (UTC)",
  "week_pct": 27,
  "week_reset": "Aug 29, 7pm (UTC)"
}
```

| Field | Meaning |
| --- | --- |
| `session_pct` | % of the current 5-hour session window used |
| `session_reset` | when that window resets |
| `week_pct` | % of the weekly all-models allowance used |
| `week_reset` | when the week resets |

**How it works.** The server runs `claude -p "/usage"` as a subprocess and
regexes the two lines out of its output:

```
You are currently using your subscription to power your Claude Code usage

Current session: 15% used · resets Aug 29, 8:40am (UTC)
Current week (all models): 27% used · resets Aug 29, 7pm (UTC)
```

So the machine running this server needs the Claude Code CLI installed **and
logged in as the same OS user the server runs as** — a systemd unit under a
different user will not see your login.

**Why it is cached.** Each poll starts a real Claude Code session: it takes
several seconds and counts against the very quota it reports. Readings are
reused for 5 minutes (`CLAUDE_USAGE_TTL` in `app/config.py`), so the first call
is slow and the next ones are instant. If a refresh fails, the last good reading
is served rather than an error; `502` comes back only when no reading has ever
succeeded.

The poll runs on `claude-haiku-4-5-20251001` to keep its own cost down.

### `GET /api/spotify`

Requires the `X-API-Key` header.

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/spotify
```

```json
{
  "is_playing": true,
  "track": "Weightless",
  "artist": "Marconi Union",
  "album": "Distance",
  "progress": 74,
  "duration": 487
}
```

When nothing is playing, the endpoint falls back to the most recently finished
track, so the display always has something to show:

```json
{
  "is_playing": false,
  "track": "Weightless",
  "artist": "Marconi Union",
  "album": "Distance",
  "progress": null,
  "played_at": "2026-09-06T09:14:22.031Z",
  "duration": 487
}
```

Read `is_playing` to tell the two apart: `progress` is set during playback,
`played_at` is set for history. Never both.

| Field | Meaning |
| --- | --- |
| `is_playing` | whether playback is currently active |
| `track` / `artist` / `album` | names; `artist` joins multiple artists with `, ` |
| `progress` | seconds into the track — live playback only, else `null` |
| `duration` | track length in seconds |
| `played_at` | ISO timestamp — history only, else `null` |

**Tokens.** Run `python -m app.spotify_auth` once from `server/` to authorise;
it prints a refresh token that goes in `.env`. Refresh tokens do not expire, so
this is a one-time step. The server exchanges it for a one-hour access token,
keeps that in memory, and renews it a minute before expiry — the ESP32 never
sees any Spotify credential.

**Scopes.** This needs both `user-read-currently-playing` and
`user-read-recently-played`. If your refresh token was minted before the second
one was added to `SPOTIFY_SCOPE`, the fallback logs a scope error and returns
`{"is_playing": false}` with empty fields — re-run `app.spotify_auth` and
replace the refresh token to fix it.

Two Spotify quirks the fallback inherits: the recently-played list excludes
skipped tracks and podcasts, and it never contains the track playing right now.
Ads and podcast episodes arrive with no track item, so those also fall back to
history.
