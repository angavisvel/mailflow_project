import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
import requests

from app.db.session import get_db
from app.db.models import User, GmailAccount
from app.config import settings
from app.auth.jwt_handler import create_access_token
from app.auth.jwt_handler import verify_access_token
from fastapi import APIRouter, Depends, HTTPException, Query, Request

router = APIRouter()

@router.get("/login")
def login(redirect_uri: Optional[str] = Query(None)):
    """
    Initiates Google OAuth flow using the redirect_uri passed by the frontend.
    """
    # Use the passed redirect_uri (port 8080) if provided, otherwise fallback to settings
    active_redirect_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=active_redirect_uri, # <-- This ensures port 8080 is sent to Google
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(url=authorization_url)

@router.post("/exchange-code")
def exchange_google_code(payload: dict, db: Session = Depends(get_db)):
    """
    Receives the Google auth code directly from the Flutter app,
    exchanges it for Google tokens, saves user/account, and returns our JWT session token.
    """
    code = payload.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri="http://127.0.0.1:8080/callback",
    )

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google token exchange failed: {str(e)}")

    credentials = flow.credentials

    # Fetch user info from Google
    user_info_resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    )
    if user_info_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info.")
    
    user_info = user_info_resp.json()
    email = user_info.get("email")

    # Upsert User & GmailAccount in SQLite
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    gmail_account = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()
    if not gmail_account:
        gmail_account = GmailAccount(
            user_id=user.id,
            email=email,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
        )
        db.add(gmail_account)
    else:
        gmail_account.access_token = credentials.token
        if credentials.refresh_token:
            gmail_account.refresh_token = credentials.refresh_token

    db.commit()

    # Issue our own JWT session token
    session_token = create_access_token(data={"sub": user.email})
    return {"session_token": session_token, "email": user.email}
@router.get("/gmail/status")
def get_gmail_status(request: Request, db: Session = Depends(get_db)):
    """
    Checks if the currently authenticated user has an active Gmail integration.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"connected": False}

    gmail_account = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()
    if not gmail_account or not gmail_account.access_token:
        return {"connected": False}

    return {
        "connected": True,
        "gmail_email": user.email  # <-- Changed from gmail_account.email to user.email
    }

@router.post("/gmail/disconnect")
def disconnect_gmail(request: Request, db: Session = Depends(get_db)):
    """
    Disconnects the user's Gmail integration.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if user:
        db.query(GmailAccount).filter(GmailAccount.user_id == user.id).delete()
        db.commit()

    return {"status": "disconnected"}