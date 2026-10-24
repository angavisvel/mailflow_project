# Backend - Phase 1 / Module 1 (User & Gmail Integration - auth only)

## What's implemented
- FastAPI app skeleton (`app/main.py`)
- SQLite/Postgres DB setup via SQLAlchemy (`app/db/session.py`)
- `User` and `GmailAccount` models only (`app/db/models.py`)
- Google OAuth2 login flow (`app/auth/oauth.py`)
- Our own session JWT issuing/verification (`app/auth/jwt_handler.py`)
- Routes: `GET /auth/login`, `GET /auth/callback`, `GET /auth/me`

## What's NOT implemented yet (later phases)
Gmail email fetching, email processing, AI/NLP extraction, task
management, reminders, follow-up drafts, sending, notifications,
dashboard. Those folders exist as empty placeholders only.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Then fill in `.env` with real values from your Google Cloud project
(see Section E of the architecture doc for exact setup steps):
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `JWT_SECRET` (any long random string)

## Run

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` - you should see the health check response.
Visit `http://localhost:8000/auth/login` to test the Google login flow
once your `.env` is filled in.

## Test before moving to Phase 2
- [ ] Server boots without errors
- [ ] `/auth/login` redirects to Google's consent screen
- [ ] After granting access, `/auth/callback` returns a session_token
- [ ] `/auth/me` (with `Authorization: Bearer <session_token>` header) returns your user info
- [ ] A row appears in both the `users` and `gmail_accounts` tables
