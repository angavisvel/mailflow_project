import re
import logging
from html.parser import HTMLParser

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GEMINI_API_KEY)
MAX_EMAIL_BODY_CHARS = 3_000
MAX_EMAIL_BODY_INPUT_CHARS = MAX_EMAIL_BODY_CHARS * 4


class _EmailBodyParser(HTMLParser):
    _SKIPPED_TAGS = {"head", "iframe", "nav", "noscript", "script", "style", "svg"}
    _BLOCK_TAGS = {"br", "div", "li", "p", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._skip_depth:
            self._skip_depth += 1
            return

        attributes = dict(attrs)
        style = (attributes.get("style") or "").replace(" ", "").lower()
        if (
            tag in self._SKIPPED_TAGS
            or "hidden" in attributes
            or (attributes.get("aria-hidden") or "").lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        ):
            self._skip_depth = 1
            return

        if tag in self._BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.text_parts.append(data)


def sanitize_email_body(body: str) -> str:
    """Strip HTML and tracking payloads, then cap the prompt input size."""
    if not body:
        return ""

    body = body[:MAX_EMAIL_BODY_INPUT_CHARS]
    if re.search(r"<\s*[a-zA-Z][^>]*>", body):
        parser = _EmailBodyParser()
        parser.feed(body)
        parser.close()
        body = "".join(parser.text_parts)

    body = re.sub(r"(?is)<[^>]+>", " ", body)
    body = re.sub(r"(?i)data:[^,\s]+;base64,[A-Za-z0-9+/=_-]+", " ", body)
    body = re.sub(r"(?i)([?&][\w.-]+=)[^&#\s]{48,}", r"\1", body)
    body = re.sub(r"(?<![\w])[A-Za-z0-9+/_=-]{80,}(?![\w])", " ", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n\n", body)
    return body.strip()[:MAX_EMAIL_BODY_CHARS]

class EmailDraftResponse(BaseModel):
    subject: str = Field(description="Reply email subject line, typically starting with 'Re: '")
    body: str = Field(description="Polite, professional email response body")

DRAFT_SYSTEM_INSTRUCTION = """
You are an executive assistant drafting a professional email response.
Follow these rules:
1. Tone must be professional, concise, and courteous.
2. Address the primary queries or action items stated in the original message.
3. Use clean text without Markdown symbols (like **bold** or asterisks).
4. Leave a placeholder like '[Your Name]' at the sign-off if the user's name is not explicitly provided.
5. Keep the reply concise and under 120 words.
"""

def _call_gemini_draft_model(model_name: str, prompt: str) -> EmailDraftResponse:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=DRAFT_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=EmailDraftResponse,
            temperature=0.3,
            max_output_tokens=256,
            http_options=types.HttpOptions(
                timeout=8_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ),
    )
    return EmailDraftResponse.model_validate_json(response.text)

def generate_reply_draft(
    original_subject: str,
    original_sender: str,
    original_body: str,
    user_intent_hint: str = ""
) -> EmailDraftResponse:
    cleaned_body = sanitize_email_body(original_body)
    prompt = f"""
Original Sender: {original_sender}
Original Subject: {original_subject}

Original Email Body:
{cleaned_body}

User's Desired Tone or Instructions for Reply:
{user_intent_hint if user_intent_hint else "Acknowledge receipt and respond appropriately."}
"""

    try:
        return _call_gemini_draft_model("gemini-3.8-flash", prompt)
    except Exception:
        logger.exception("Gemini reply generation failed")
        raise