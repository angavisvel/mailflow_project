"""
SQLAlchemy models.

Module 1, 2, 3 & 4 scope: User, GmailAccount, Email, and Task.
Followup, Notification models will be added in later modules.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    gmail_accounts = relationship("GmailAccount", back_populates="user")
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class GmailAccount(Base):
    __tablename__ = "gmail_accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)

    connected_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="gmail_accounts")


class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    gmail_message_id = Column(String, unique=True, index=True, nullable=False)
    thread_id = Column(String, index=True, nullable=False)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    snippet = Column(String, nullable=True)
    body_text = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False)
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="emails")
    tasks = relationship("Task", back_populates="email")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    email_id = Column(UUID(as_uuid=False), ForeignKey("emails.id"), nullable=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String, default="medium")  # low, medium, high
    status = Column(String, default="pending")   # pending, completed, dismissed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="tasks")
    email = relationship("Email", back_populates="tasks")
    # In Task model, add:
    notifications = relationship("Notification", back_populates="task", cascade="all, delete-orphan")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True)

    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="deadline_reminder")  # deadline_reminder, overdue_alert, status_update
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
    task = relationship("Task", back_populates="notifications")