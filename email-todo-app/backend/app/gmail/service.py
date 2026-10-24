import base64
from datetime import datetime
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from app.gmail.client import build_gmail_client


def parse_email_payload(msg_data: dict) -> dict:
    payload = msg_data.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="ignore"
                )
                break
            elif part.get("mimeType") == "text/html" and "data" in part.get("body", {}):
                html_content = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                    "utf-8", errors="ignore"
                )
                soup = BeautifulSoup(html_content, "html.parser")
                body = soup.get_text(separator="\n").strip()
    elif "body" in payload and "data" in payload["body"]:
        raw_body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
            "utf-8", errors="ignore"
        )
        if payload.get("mimeType") == "text/html":
            soup = BeautifulSoup(raw_body, "html.parser")
            body = soup.get_text(separator="\n").strip()
        else:
            body = raw_body

    internal_date_ms = int(msg_data.get("internalDate", 0))
    received_at = (
        datetime.fromtimestamp(internal_date_ms / 1000.0)
        if internal_date_ms
        else datetime.utcnow()
    )

    return {
        "gmail_message_id": msg_data["id"],
        "thread_id": msg_data.get("threadId", ""),
        "sender": headers.get("from", "Unknown"),
        "recipient": headers.get("to", ""),
        "subject": headers.get("subject", "(No Subject)"),
        "snippet": msg_data.get("snippet", ""),
        "body_text": body.strip(),
        "received_at": received_at,
    }


def create_gmail_draft(
    access_token: str,
    refresh_token: str,
    to: str,
    subject: str,
    body: str,
    thread_id: str = None,
) -> dict:
    service = build_gmail_client(access_token, refresh_token, timeout=5)

    message = MIMEText(body, _charset="utf-8")
    message["To"] = to
    message["Subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw_message,
        }
    }
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    return service.users().drafts().create(userId="me", body=draft_body).execute()