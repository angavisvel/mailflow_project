import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.ai_nlp.draft_service import generate_reply_draft
from app.auth.jwt_handler import get_current_user
from app.db.models import Email, GmailAccount, User
from app.db.session import get_db
from app.gmail.service import create_gmail_draft

router = APIRouter()


class DraftRequest(BaseModel):
    instruction: Optional[str] = Field(default=None, max_length=1_000)
    user_hint: Optional[str] = Field(default=None, max_length=1_000)


@router.post("/draft-reply/{email_id}")
async def create_email_draft(
    email_id: str,
    request: DraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        email = db.get(Email, email_id)
        if not email or email.user_id != user.id:
            raise HTTPException(status_code=404, detail="Email not found")

        account = db.query(GmailAccount).filter(GmailAccount.user_id == user.id).first()
        if not account or not account.access_token:
            raise HTTPException(status_code=401, detail="Gmail not authenticated")

        instruction = (
            request.instruction
            or request.user_hint
            or "Politely acknowledge and confirm details."
        )
        original_body = email.body_text or email.snippet or ""
        try:
            draft_content = await run_in_threadpool(
                generate_reply_draft,
                original_subject=email.subject or "",
                original_sender=email.sender or "",
                original_body=original_body,
                user_intent_hint=instruction,
            )
            generated_body = draft_content.body.strip()
            if not generated_body:
                raise ValueError("Gemini returned an empty reply.")
        except Exception:
            traceback.print_exc()
            generated_body = (
                "Hello,\n\n"
                "Thank you for your email. I acknowledge receipt and will review "
                "the details. Please let me know if there is anything else I can "
                "help with.\n\n"
                "Best regards,\n[Your Name]"
            )

        try:
            gmail_draft = await run_in_threadpool(
                create_gmail_draft,
                access_token=account.access_token,
                refresh_token=account.refresh_token,
                to=email.sender,
                subject=f"Re: {email.subject or 'Your Inquiry'}",
                body=generated_body,
                thread_id=email.thread_id,
            )
        except RefreshError as exc:
            traceback.print_exc()
            raise HTTPException(
                status_code=401,
                detail="Gmail not authenticated",
            ) from exc
        except HttpError as exc:
            traceback.print_exc()
            if exc.resp.status == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Gmail not authenticated",
                ) from exc
            raise HTTPException(
                status_code=502,
                detail=f"Gmail API failed to create the draft: {exc}",
            ) from exc

        draft_id = gmail_draft.get("id")
        if not draft_id:
            raise HTTPException(
                status_code=502,
                detail="Gmail API did not return a draft ID.",
            )

        return {
            "status": "success",
            "message": "Draft created successfully",
            "draft_id": draft_id,
            "preview": generated_body,
        }
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"Draft creation failed: {type(exc).__name__}: {exc}",
        ) from exc
