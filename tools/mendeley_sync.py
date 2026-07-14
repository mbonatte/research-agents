"""Guided Mendeley-to-Notion archive synchronization CLI.

Run `python -m tools.mendeley_sync authorize` once, then
`python -m tools.mendeley_sync sync` whenever the archive should be refreshed.
"""
import argparse
import json
import os
import secrets
import subprocess
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

from tools.mendeley import mendeley_document_to_archive_record
from tools.notion import update_mendeley_article

TOKEN_URL = "https://api.mendeley.com/oauth/token"
DOCUMENTS_URL = "https://api.mendeley.com/documents"
FILES_URL = "https://api.mendeley.com/files"
MENDELEY_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"


def token_file() -> Path:
    return Path(os.getenv("MENDELEY_TOKEN_FILE", ".secrets/mendeley_tokens.json"))


def require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Follow the Mendeley setup section in README.md.")
    return value


def request_token(data: dict[str, str]) -> dict:
    """Request an OAuth token through curl, which Mendeley's Cloudflare accepts."""
    command = [
        "curl.exe", "--silent", "--show-error", "--fail-with-body",
        "--request", "POST", TOKEN_URL,
        "--header", "Content-Type: application/x-www-form-urlencoded",
        "--header", "Accept: application/json",
        "--user-agent", MENDELEY_USER_AGENT,
    ]
    for key, value in data.items():
        command.extend(["--data-urlencode", f"{key}={value}"])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        detail = (result.stdout or result.stderr).strip().replace("\n", " ")[:500]
        raise RuntimeError(f"Mendeley token request failed: {detail or 'curl returned no detail'}")
    try:
        token_data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Mendeley token endpoint did not return JSON.") from exc
    if not token_data.get("access_token"):
        raise RuntimeError("Mendeley token response did not include an access token.")
    return token_data


def save_tokens(tokens: dict) -> None:
    path = token_file(); path.parent.mkdir(parents=True, exist_ok=True)
    tokens["expires_at"] = int(time.time()) + int(tokens.get("expires_in", 3600))
    path.write_text(json.dumps(tokens), encoding="utf-8")


def valid_access_token() -> str:
    path = token_file()
    tokens = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if tokens.get("access_token") and time.time() < tokens.get("expires_at", 0) - 60:
        return tokens["access_token"]
    refresh = tokens.get("refresh_token")
    if not refresh:
        raise RuntimeError("No Mendeley token found. Run: python -m tools.mendeley_sync authorize")
    refreshed = request_token({
        "grant_type": "refresh_token",
        "refresh_token": refresh,
        "redirect_uri": os.getenv("MENDELEY_REDIRECT_URI", "http://127.0.0.1:8000/callback"),
        "client_id": require("MENDELEY_CLIENT_ID"),
        "client_secret": require("MENDELEY_CLIENT_SECRET"),
    })
    refreshed.setdefault("refresh_token", refresh); save_tokens(refreshed)
    return refreshed["access_token"]


def authorize() -> None:
    redirect = os.getenv("MENDELEY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
    client_id = require("MENDELEY_CLIENT_ID")
    code: dict[str, str] = {}
    state = secrets.token_urlsafe(32)
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            code.update({key: values[0] for key, values in parse_qs(urlparse(self.path).query).items()})
            self.send_response(200); self.end_headers(); self.wfile.write(b"Authorization received. You can close this tab.")
        def log_message(self, format, *args): pass
    url = "https://api.mendeley.com/oauth/authorize?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": "all",
        "state": state,
    })
    print("Opening Mendeley authorization in your browser..."); webbrowser.open(url)
    server = HTTPServer(("127.0.0.1", urlparse(redirect).port or 8000), Callback)
    while "code" not in code and "error" not in code: server.handle_request()
    if "error" in code: raise RuntimeError(f"Mendeley authorization failed: {code['error']}")
    if not secrets.compare_digest(code.get("state", ""), state):
        raise RuntimeError("Mendeley authorization failed: callback state did not match the authorization request.")
    token_data = request_token({
        "grant_type": "authorization_code",
        "code": code["code"],
        "redirect_uri": redirect,
        "client_id": client_id,
        "client_secret": require("MENDELEY_CLIENT_SECRET"),
    })
    save_tokens(token_data); print(f"Authorized. Tokens saved to {token_file()}.")


def fetch_all(url: str, token: str, accept: str) -> list[dict]:
    result=[]; seen=set(); next_url=url
    while next_url:
        response=requests.get(next_url, headers={"Authorization":f"Bearer {token}","Accept":accept}, timeout=30); response.raise_for_status()
        for item in response.json():
            if item.get("id") not in seen: seen.add(item.get("id")); result.append(item)
        next_url=next((part.split(";")[0].strip()[1:-1] for part in response.headers.get("Link", "").split(",") if 'rel="next"' in part), None)
    return result


def sync() -> None:
    token=valid_access_token()
    documents=fetch_all(f"{DOCUMENTS_URL}?limit=100&view=all", token, "application/vnd.mendeley-document.1+json")
    files=fetch_all(f"{FILES_URL}?limit=100", token, "application/vnd.mendeley-file.1+json")
    files_by_document={}
    for item in files: files_by_document.setdefault(item.get("document_id"), []).append(item)
    created=updated=0
    for index, document in enumerate(documents, 1):
        result=update_mendeley_article(**mendeley_document_to_archive_record(document, files_by_document))
        created += result["status"] == "created"; updated += result["status"] == "updated"
        if index % 25 == 0: print(f"Synced {index}/{len(documents)}")
    print(f"Sync complete: {len(documents)} documents; {created} created; {updated} updated.")


if __name__ == "__main__":
    load_dotenv()
    parser=argparse.ArgumentParser(); parser.add_argument("command", choices=("authorize", "sync")); args=parser.parse_args()
    authorize() if args.command == "authorize" else sync()
