from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, Email, Task
from app.auth.jwt_handler import get_current_user
from app.ai_nlp.service import analyze_email_content

router = APIRouter()

def _save_extracted_tasks(tasks_data, user_id: str, email_id: str, db: Session):
    saved_tasks = []
    for task_data in tasks_data:
        parsed_due_date = None
        if task_data.due_date:
            try:
                parsed_due_date = datetime.fromisoformat(task_data.due_date)
            except ValueError:
                parsed_due_date = None

        new_task = Task(
            user_id=user_id,
            email_id=email_id,
            title=task_data.title,
            description=task_data.context_snippet,
            priority=task_data.priority.lower(),
            due_date=parsed_due_date,
            status="pending",
        )
        db.add(new_task)
        saved_tasks.append(new_task)
    return saved_tasks


@router.post("/process/{email_id}")
def process_single_email(
    email_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    email = db.query(Email).filter(Email.id == email_id, Email.user_id == user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    analysis = analyze_email_content(
        subject=email.subject or "",
        sender=email.sender or "",
        body=email.body_text or email.snippet or "",
        received_at=str(email.received_at),
    )

    if analysis.is_actionable and analysis.tasks:
        _save_extracted_tasks(analysis.tasks, user.id, email.id, db)

    email.is_processed = True
    db.commit()

    return {
        "email_id": email.id,
        "subject": email.subject,
        "analysis": analysis.model_dump()
    }


@router.post("/process-all")
def process_unprocessed_emails(
    limit: int = 5,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    unprocessed = (
        db.query(Email)
        .filter(Email.user_id == user.id, Email.is_processed == False)
        .limit(limit)
        .all()
    )

    results = []
    for email in unprocessed:
        try:
            analysis = analyze_email_content(
                subject=email.subject or "",
                sender=email.sender or "",
                body=email.body_text or email.snippet or "",
                received_at=str(email.received_at),
            )

            if analysis.is_actionable and analysis.tasks:
                _save_extracted_tasks(analysis.tasks, user.id, email.id, db)

            email.is_processed = True
            db.commit()

            results.append({
                "email_id": email.id,
                "subject": email.subject,
                "status": "success",
                "analysis": analysis.model_dump()
            })
        except Exception as exc:
            db.rollback()
            results.append({
                "email_id": email.id,
                "subject": email.subject,
                "status": "failed",
                "error": str(exc)
            })

    return {"processed_count": len(results), "items": results}
