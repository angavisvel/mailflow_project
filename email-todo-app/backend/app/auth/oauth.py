"""
Google OAuth2 flow: builds the consent screen URL and exchanges
the returned auth code for access + refresh tokens.

This module only talks to Google. Storing tokens / issuing our
own session JWT happens in routes.py.
"""
import os

# Allow scope changes and local HTTP without raising OAuth2 exceptions
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google_auth_oauthlib.flow import Flow
from app.config import settings


def build_flow(state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
    )


def get_authorization_url() -> tuple[str, str]:
    """Returns (authorization_url, state) - send the user to authorization_url."""
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",       # needed to get a refresh_token
        include_granted_scopes="true",
        prompt="consent",            # forces refresh_token on repeat logins in dev
    )
    return auth_url, state


def exchange_code_for_tokens(code: str, state: str) -> dict:
    """Exchanges the auth code Google sent back for access + refresh tokens."""
    flow = build_flow(state=state)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI  # Ensure redirect_uri matches exactly
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "id_token": creds.id_token,
    }