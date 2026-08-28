# ESP32 Weather Service

A tiny FastAPI service that fetches current weather from
[Open-Meteo](https://open-meteo.com/en/docs) and returns a small JSON payload
that an ESP32 can parse directly.

The ESP32 never talks to the weather provider — it only talks to this server.

## Environment variables

Copy `.env.example` to `.env` and fill it in:

| Variable | Description |
| --- | --- |
| `WEATHER_LATITUDE` | Latitude of the location to report |
| `WEATHER_LONGITUDE` | Longitude of the location to report |
| `API_KEY` | Secret that clients must send as `X-API-Key` |

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

Temperature is in Celsius, wind speed in km/h, humidity and rain probability in
percent. If Open-Meteo is unreachable or returns something unusable, the server
responds with `502` and logs the details on the server side.
