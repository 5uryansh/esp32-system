import base64
import http.server
import threading
import time
import urllib.parse
import webbrowser
import requests
from . import config

SPOTIFY_CLIENT_ID = config.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = config.SPOTIFY_CLIENT_SECRET

SPOTIFY_REDIRECT_URI = config.SPOTIFY_REDIRECT_URI
SPOTIFY_SCOPE = config.SPOTIFY_SCOPE

authorization_code = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code

        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        authorization_code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        if authorization_code:
            self.wfile.write(
                b"<h1>Spotify authorization successful.</h1>"
                b"<p>You can close this window.</p>"
            )
        else:
            self.wfile.write(
                b"<h1>Authorization failed.</h1>"
            )

    def log_message(self, format, *args):
        pass


server = http.server.HTTPServer(
    ("127.0.0.1", 8888),
    CallbackHandler
)

threading.Thread(
    target=server.handle_request,
    daemon=True
).start()

params = {
    "client_id": SPOTIFY_CLIENT_ID,
    "response_type": "code",
    "redirect_uri": SPOTIFY_REDIRECT_URI,
    "scope": SPOTIFY_SCOPE,
}

auth_url = (
    "https://accounts.spotify.com/authorize?"
    + urllib.parse.urlencode(params)
)

print("Opening Spotify authorization...")
webbrowser.open(auth_url)

while authorization_code is None:
    time.sleep(0.1)

server.server_close()

credentials = base64.b64encode(
    f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
).decode()

response = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    },
    data={
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    },
)

payload = response.json()
refresh_token = payload.get("refresh_token")

if refresh_token:
    print("\nAdd this line to server/.env:\n")
    print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print(f"\nGranted scopes: {payload.get('scope')}")
else:
    print("\nNo refresh token in the response:")
    print(payload)