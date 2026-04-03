#!/usr/bin/env python3
"""
YouTube OAuth2 authorization flow.
Run once to get your refresh token and save it to .env.

Usage: python auth/youtube_auth.py
"""
import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print("ERROR: Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env first.")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(port=8081)

    print("\n=== SUCCESS ===")
    print(f"Refresh token: {credentials.refresh_token}")
    print("\nAdd to your .env:")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
