from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, Task
from app.auth.jwt_handler import get_current_user
from app.ai_nlp.task_extractor_service import extract_task_from_email
from datetime import datetime
from app.db.models import Email # Ensure Email model is imported if not already

router = APIRouter()

class TaskUpdateSchema(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None  # "pending", "completed", "dismissed"

@router.get("/")
def get_tasks(
    status: Optional[str] = Query(None, description="Filter by: pending, completed, dismissed"),
    priority: Optional[str] = Query(None, description="Filter by: high, medium, low"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.user_id == user.id)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    
    return query.order_by(Task.created_at.desc()).all()

@router.patch("/{task_id}")
def update_task(
    task_id: str,
    update_data: TaskUpdateSchema,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    db.delete(task)
    db.commit()
    return {"status": "deleted", "task_id": task_id}

@router.post("/extract-missing")
def extract_missing_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Scans all stored emails that don't have tasks yet and runs AI extraction."""
    emails = db.query(Email).filter(Email.user_id == user.id).all()
    extracted_count = 0

    for email in emails:
        # Check if a task already exists for this email
        existing_task = db.query(Task).filter(Task.email_id == email.id).first()
        if existing_task:
            continue

        # Run AI extraction
        extracted = extract_task_from_email(
            subject=email.subject or "",
            sender=email.sender or "",
            body=email.body_text or email.snippet or "",
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
                email_id=email.id,
                title=extracted.title,
                description=extracted.description,
                due_date=parsed_date,
                priority=extracted.priority or "medium",
                status="pending",
            )
            db.add(task_record)
            extracted_count += 1

    db.commit()
    return {"status": "success", "new_tasks_extracted": extracted_count}