"""OpenAI Codex OAuth flow helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import string
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"
JWT_CLAIM_PATH = "https://api.openai.com/auth"
SUCCESS_HTML = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8' />"
    "<meta name='viewport' content='width=device-width, initial-scale=1' />"
    "<title>Authentication successful</title></head><body>"
    "<p>Authentication successful. Return to your terminal to continue.</p>"
    "</body></html>"
)


def _generate_pkce() -> tuple[str, str]:
    verifier = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(64)
    )
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.rstrip(b"=").decode()


def _create_state() -> str:
    return secrets.token_hex(16)


def _decode_jwt(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        return json.loads(decoded)
    except Exception:
        return None


def _get_account_id(access_token: str) -> str | None:
    payload = _decode_jwt(access_token)
    auth = payload.get(JWT_CLAIM_PATH) if payload else None
    account_id = auth.get("chatgpt_account_id") if auth else None
    if isinstance(account_id, str) and account_id:
        return account_id
    return None


def _exchange_authorization_code(
    code: str, verifier: str, redirect_uri: str = REDIRECT_URI
) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    if not resp.ok:
        return {"type": "failed"}
    json_data = resp.json()
    if not all(
        [
            json_data.get("access_token"),
            json_data.get("refresh_token"),
            isinstance(json_data.get("expires_in"), int),
        ]
    ):
        return {"type": "failed"}
    return {
        "type": "success",
        "access": json_data["access_token"],
        "refresh": json_data["refresh_token"],
        "expires_in": int(json_data["expires_in"]),
    }


def _refresh_access_token(refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    if not resp.ok:
        return {"type": "failed"}
    json_data = resp.json()
    if not all(
        [
            json_data.get("access_token"),
            json_data.get("refresh_token"),
            isinstance(json_data.get("expires_in"), int),
        ]
    ):
        return {"type": "failed"}
    return {
        "type": "success",
        "access": json_data["access_token"],
        "refresh": json_data["refresh_token"],
        "expires_in": int(json_data["expires_in"]),
    }


def _create_authorization_flow(originator: str = "pi") -> tuple[str, str, str]:
    verifier, challenge = _generate_pkce()
    state = _create_state()
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": originator,
    }
    url = AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
    return verifier, state, url


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    code = None
    state = None

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)
        if url.path != "/auth/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        if params.get("state", [None])[0] != self.state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch")
            return
        code = params.get("code", [None])[0]
        if not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(SUCCESS_HTML.encode())
        _OAuthCallbackHandler.code = code

    def log_message(self, _format, *_args):
        return


def _start_local_oauth_server(state: str) -> HTTPServer:
    _OAuthCallbackHandler.state = state
    _OAuthCallbackHandler.code = None
    server = HTTPServer(("127.0.0.1", 1455), _OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _parse_auth_input(value: str) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if "code=" in raw:
        parsed = urllib.parse.urlparse(raw)
        params = urllib.parse.parse_qs(parsed.query)
        return params.get("code", [None])[0]
    return raw


def login_openai_codex() -> dict:
    verifier, state, url = _create_authorization_flow()
    print(f"Open this URL in browser and finish login:\n{url}\n")
    webbrowser.open(url)
    server = _start_local_oauth_server(state)
    print("Waiting for OAuth callback...")

    for _ in range(600):
        if _OAuthCallbackHandler.code:
            break
        threading.Event().wait(0.1)
    server.shutdown()
    server.server_close()

    code = _OAuthCallbackHandler.code
    if not code:
        manual = input("No callback received. Paste auth code or callback URL: ")
        code = _parse_auth_input(manual)

    if not code:
        raise RuntimeError("Missing authorization code")

    token_result = _exchange_authorization_code(code, verifier)
    if token_result["type"] != "success":
        raise RuntimeError("Token exchange failed")

    account_id = _get_account_id(token_result["access"])
    if not account_id:
        raise RuntimeError("Failed to extract accountId from token")

    return {
        "access": token_result["access"],
        "refresh": token_result["refresh"],
        "expires_in": token_result["expires_in"],
        "account_id": account_id,
    }


def refresh_openai_codex_token(refresh_token: str) -> dict:
    result = _refresh_access_token(refresh_token)
    if result["type"] != "success":
        raise RuntimeError("Failed to refresh OpenAI Codex token")
    account_id = _get_account_id(result["access"])
    if not account_id:
        raise RuntimeError("Failed to extract accountId from token")
    return {
        "access": result["access"],
        "refresh": result["refresh"],
        "expires_in": result["expires_in"],
        "account_id": account_id,
    }
