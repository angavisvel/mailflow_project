from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Task, Notification

def check_deadlines_and_generate_alerts(user_id: str, db: Session) -> list[Notification]:
    now = datetime.utcnow()
    reminder_window = now + timedelta(days=2)  # Alert for deadlines within next 48 hours

    # 1. Upcoming pending tasks
    upcoming_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == "pending",
            Task.due_date != None,
            Task.due_date >= now,
            Task.due_date <= reminder_window,
        )
        .all()
    )

    created_notifications = []

    for task in upcoming_tasks:
        # Check if an unread reminder already exists for this task
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.task_id == task.id,
                Notification.type == "deadline_reminder",
                Notification.is_read == False,
            )
            .first()
        )
        if not existing:
            notice = Notification(
                user_id=user_id,
                task_id=task.id,
                title=f"Upcoming Deadline: {task.title}",
                message=f"Task '{task.title}' is due on {task.due_date.strftime('%Y-%m-%d %H:%M')}. Priority: {task.priority.upper()}.",
                type="deadline_reminder",
            )
            db.add(notice)
            created_notifications.append(notice)

    # 2. Overdue pending tasks
    overdue_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == "pending",
            Task.due_date != None,
            Task.due_date < now,
        )
        .all()
    )

    for task in overdue_tasks:
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.task_id == task.id,
                Notification.type == "overdue_alert",
                Notification.is_read == False,
            )
            .first()
        )
        if not existing:
            notice = Notification(
                user_id=user_id,
                task_id=task.id,
                title=f"Overdue Alert: {task.title}",
                message=f"Task '{task.title}' passed its deadline ({task.due_date.strftime('%Y-%m-%d %H:%M')}).",
                type="overdue_alert",
            )
            db.add(notice)
            created_notifications.append(notice)

    db.commit()
    return created_notifications