from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.jwt_handler import get_current_user
from app.db.models import User, Email, GmailAccount
from app.gmail.client import build_gmail_client
from app.gmail.service import parse_email_payload, create_gmail_draft
from app.ai_nlp.draft_service import generate_reply_draft
from app.ai_nlp.task_extractor_service import extract_task_from_email
from app.db.models import Task
from datetime import datetime

router = APIRouter()


class DraftRequest(BaseModel):
    user_hint: Optional[str] = "Politely acknowledge and confirm details."


@router.post("/sync")
def sync_emails(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.gmail_accounts:
        raise HTTPException(status_code=400, detail="Gmail account not connected.")

    gmail_account = user.gmail_accounts[0]
    service = build_gmail_client(gmail_account.access_token, gmail_account.refresh_token)

    # Fetch latest 10 messages from Inbox
    results = service.users().messages().list(userId="me", maxResults=10, q="label:INBOX").execute()
    messages = results.get("messages", [])

    synced_emails = []
    tasks_created_count = 0

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        
        # Check if email is already stored
        existing_email = db.query(Email).filter(Email.gmail_message_id == msg_id).first()
        
        if not existing_email:
            full_msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            parsed = parse_email_payload(full_msg)

            existing_email = Email(user_id=user.id, **parsed)
            db.add(existing_email)
            db.flush() # Flush to get existing_email.id
            synced_emails.append(parsed.get("subject"))

        # --- ENSURE TASK EXTRACTION RUNS FOR EVERY EMAIL ---
        # Check if a task already exists for this email
        existing_task = db.query(Task).filter(Task.email_id == existing_email.id).first()
        if not existing_task:
            extracted = extract_task_from_email(
                subject=existing_email.subject or "",
                sender=existing_email.sender or "",
                body=existing_email.body_text or existing_email.snippet or "",
            )

            if extracted.is_actionable and extracted.title:
                parsed_date = None
                if extracted.due_date:
                    try:
                        parsed_date = datetime.strptime(extracted.due_date, "%Y-%m-%d")
                    except ValueError:
                        pass

                task_record = Task(
                    user_id=user.id,
                    email_id=existing_email.id,
                    title=extracted.title,
                    description=extracted.description,
                    due_date=parsed_date,
                    priority=extracted.priority or "medium",
                    status="pending",
                )
                db.add(task_record)
                tasks_created_count += 1

    db.commit()
    return {
        "status": "success",
        "new_emails_synced": len(synced_emails),
        "tasks_extracted": tasks_created_count,
        "subjects": synced_emails,
    }


@router.get("/list")
def list_stored_emails(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    emails = db.query(Email).filter(Email.user_id == user.id).order_by(Email.received_at.desc()).all()
    return {"emails": emails}


@router.post("/draft-preview/{email_id}")
def preview_email_draft(
    email_id: str,
    request: DraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates an AI reply draft preview without saving to Gmail."""
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    draft = generate_reply_draft(
        original_subject=email.subject or "",
        original_sender=email.sender or "",
        original_body=email.body_text or email.snippet or "",
        user_intent_hint=request.user_hint,
    )
    return {"email_id": email.id, "recipient": email.sender, "draft": draft.model_dump()}


@router.post("/save-draft/{email_id}")
def save_draft_to_gmail(
    email_id: str,
    request: DraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates an AI reply draft and commits it to the user's Gmail Drafts folder."""
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    account = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=400, detail="Gmail account not connected.")

    draft_content = generate_reply_draft(
        original_subject=email.subject or "",
        original_sender=email.sender or "",
        original_body=email.body_text or email.snippet or "",
        user_intent_hint=request.user_hint,
    )

    gmail_draft = create_gmail_draft(
        access_token=account.access_token,
        refresh_token=account.refresh_token,
        to=email.sender,
        subject=f"Re: {email.subject or ''}",
        body=draft_content.body,
        thread_id=email.thread_id,
    )

    return {
        "status": "success",
        "success": True,
        "gmail_draft_id": gmail_draft.get("id"),
        "draft_content": draft_content.model_dump(),
    }