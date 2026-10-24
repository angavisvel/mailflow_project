from typing import List, Optional
from pydantic import BaseModel, Field

class ExtractedTask(BaseModel):
    title: str = Field(description="Clear, concise imperative action item (e.g., 'Register for exam')")
    due_date: Optional[str] = Field(None, description="ISO-8601 formatted deadline date (YYYY-MM-DD) if stated or inferable, else null")
    priority: str = Field(description="Priority rating: 'high', 'medium', or 'low'")
    context_snippet: Optional[str] = Field(None, description="Short snippet from email text supporting this task")

class EmailAnalysisResult(BaseModel):
    category: str = Field(description="One of: 'actionable', 'newsletter', 'marketing', 'transactional', 'notification'")
    is_actionable: bool = Field(description="True if the email requires user follow-up or task execution, False otherwise")
    summary: str = Field(description="One-sentence summary of the email's core message")
    tasks: List[ExtractedTask] = Field(default_factory=list, description="Action items extracted if actionable")