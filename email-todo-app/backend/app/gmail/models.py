from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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

    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")

    user = relationship("User", back_populates="emails")