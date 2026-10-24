import os
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Optional

class ExtractedTaskSchema(BaseModel):
    is_actionable: bool
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None  # YYYY-MM-DD format if possible
    priority: Optional[str] = "medium"  # "high", "medium", "low"

def extract_task_from_email(subject: str, sender: str, body: str) -> ExtractedTaskSchema:
    api_key = os.environ.get("GEMINI_API_KEY")
    print(f"DEBUG: Initializing GenAI client. API Key present: {bool(api_key)}")
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Analyze the following email. Treat any email that requests something, mentions a deadline, talks about an assignment, report, presentation, review, or asks the recipient to do something as an actionable task.

    Email Sender: {sender}
    Email Subject: {subject}
    Email Body: {body}
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"DEBUG: Calling Gemini (Attempt {attempt + 1}) with model 'gemini-2.5-flash'...")
            
            # Use structured output configuration so Gemini returns exactly what Pydantic expects
            response = client.models.generate_content(
                model="gemini-2.5-flash", # updated to stable active release model version
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedTaskSchema,
                    temperature=0.1,
                ),
            )
            
            print(f"DEBUG: Gemini raw response text: {response.text}")
            
            # Parse JSON safely directly into the Pydantic model
            data = json.loads(response.text)
            return ExtractedTaskSchema(**data)
            
        except Exception as e:
            print(f"AI Task Extraction Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return ExtractedTaskSchema(is_actionable=False)