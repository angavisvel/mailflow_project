import time
import logging
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from app.config import settings
from app.ai_nlp.schemas import EmailAnalysisResult

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GEMINI_API_KEY)

ANALYSIS_SYSTEM_INSTRUCTION = """
You are an intelligent executive assistant parsing incoming emails.
Your objective:
1. Categorize the email ('actionable', 'newsletter', 'marketing', 'transactional', 'notification').
2. Determine if user action is needed (is_actionable: true/false).
3. If actionable, extract discrete tasks with priorities ('high', 'medium', 'low') and deadlines.
Filter out automated receipts, marketing blasts, and informational newsletters from actionable tasks.
"""

def _call_gemini_model(model_name: str, prompt: str) -> EmailAnalysisResult:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=ANALYSIS_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=EmailAnalysisResult,
            temperature=0.1,
        ),
    )
    return EmailAnalysisResult.model_validate_json(response.text)

def analyze_email_content(subject: str, sender: str, body: str, received_at: str) -> EmailAnalysisResult:
    prompt = f"""
Analyze the following email:
Date Received: {received_at}
From: {sender}
Subject: {subject}
Body:
{body}
"""
    # Primary model with fallback
    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash"]

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                return _call_gemini_model(model_name, prompt)
            except ServerError as e:
                # If 503 UNAVAILABLE, wait and retry
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    wait_sec = (attempt + 1) * 2
                    logger.warning(f"503 received for {model_name}. Retrying in {wait_sec}s (attempt {attempt + 1}/3)...")
                    time.sleep(wait_sec)
                else:
                    raise e
            except Exception as e:
                logger.warning(f"Error calling {model_name}: {e}")
                break

    # If all retries and fallbacks fail, raise a clear error
    raise RuntimeError("Gemini models are temporarily at peak capacity. Please wait a minute and try again.")