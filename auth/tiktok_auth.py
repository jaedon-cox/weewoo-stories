#!/usr/bin/env python3
"""
TikTok OAuth2 authorization flow.
Run once to get your refresh token and save it to .env.

Usage: python auth/tiktok_auth.py
"""
import os
import sys
import urllib.parse
import http.server
import threading
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = ["user.info.basic", "video.publish", "video.upload"]

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

received_code = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global received_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        received_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Authorization complete. You can close this tab.</h2>")

    def log_message(self, *args):
        pass


def main():
    if not CLIENT_KEY or not CLIENT_SECRET:
        print("ERROR: Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env first.")
        sys.exit(1)

    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    auth_url = (
        f"{AUTH_URL}?client_key={CLIENT_KEY}"
        f"&response_type=code"
        f"&scope={','.join(SCOPES)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state=autostory"
    )
    print(f"\nOpening browser for TikTok authorization...\n{auth_url}\n")
    webbrowser.open(auth_url)
    thread.join(timeout=120)

    if not received_code:
        print("ERROR: No code received. Did you authorize in the browser?")
        sys.exit(1)

    resp = requests.post(TOKEN_URL, data={
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": received_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    resp.raise_for_status()
    data = resp.json()

    print("\n=== SUCCESS ===")
    print(f"Access token:  {data['access_token']}")
    print(f"Refresh token: {data['refresh_token']}")
    print(f"Expires in:    {data['expires_in']}s")
    print("\nAdd to your .env:")
    print(f"TIKTOK_REFRESH_TOKEN={data['refresh_token']}")


if __name__ == "__main__":
    main()
