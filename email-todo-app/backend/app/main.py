"""
Entry point for the Email -> To-Do List backend.

Phase 1 / Module 1 to 5 scope:
- App boots
- Auth routes (Google OAuth login)
- Gmail routes (email syncing and retrieval)
- AI routes (email classification and task extraction)
- Tasks routes (task persistence & CRUD)
- Notifications routes (deadline alerts & reminders)
"""
import os

# Allow scope changes and local HTTP without raising OAuth2 exceptions
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import FastAPI

import app.db.models  # Imports all models (User, Email, Task, Notification, etc.)
from app.auth.routes import router as auth_router
from app.gmail.routes import router as gmail_router
from app.ai_nlp.routes import router as ai_router
from app.tasks.routes import router as tasks_router
from app.notifications.routes import router as notifications_router
from app.db.session import init_db
from app.gmail.routes import router as email_router
from app.email_drafts.router import router as email_drafts_router



app = FastAPI(title="Email -> To-Do List", version="0.1.0")


@app.on_event("startup")
def on_startup():
    # Creates tables for all defined models
    init_db()


@app.get("/")
def health_check():
    return {"status": "ok", "phase": "1", "module": "5 - Notifications & Reminders"}


# Register routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(gmail_router, prefix="/gmail", tags=["gmail"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
app.include_router(email_router, prefix="/emails", tags=["Emails"])
app.include_router(email_drafts_router, prefix="/emails")
