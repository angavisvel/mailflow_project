"""
Gmail API client utilities for authenticating and communicating with Google APIs.
"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2

from app.config import settings


def build_gmail_client(
    access_token: str, refresh_token: str, timeout: float | None = None
):
    """Builds and returns an authorized Google API Gmail service client."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.GOOGLE_SCOPES,
    )
    if timeout is not None:
        http = AuthorizedHttp(creds, http=httplib2.Http(timeout=timeout))
        return build("gmail", "v1", http=http)
    return build("gmail", "v1", credentials=creds)


def get_gmail_profile(access_token: str, refresh_token: str) -> dict:
    """Fetches user profile information directly from Gmail."""
    service = build_gmail_client(access_token, refresh_token)
    return service.users().getProfile(userId="me").execute()