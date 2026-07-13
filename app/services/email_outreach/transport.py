"""SMTP/IMAP transport for connected email accounts."""

from __future__ import annotations

import base64
import email
import imaplib
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

import httpx

from app.models.email_outreach import EmailAccount, EmailProvider
from app.utils.secret_encryption import decrypt_secret, decrypt_json

logger = logging.getLogger(__name__)


class EmailTransportError(Exception):
    pass


def _smtp_send(
    account: EmailAccount,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    creds = decrypt_json(account.encrypted_credentials or "")
    password = creds.get("password") or decrypt_secret(account.oauth_access_token_encrypted or "")

    if account.provider in (EmailProvider.gmail_oauth, EmailProvider.outlook_oauth):
        return _oauth_smtp_send(account, to_email, subject, body_text, body_html, in_reply_to, references)

    if not account.smtp_host or not password:
        raise EmailTransportError("SMTP credentials not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((account.display_name or account.email_address, account.email_address))
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid()
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(account.smtp_host, account.smtp_port or 587, timeout=30) as server:
        if account.use_tls:
            server.starttls(context=context)
        server.login(account.email_address, password)
        server.sendmail(account.email_address, [to_email], msg.as_string())

    return msg["Message-ID"]


def _oauth_smtp_send(
    account: EmailAccount,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    access_token = decrypt_secret(account.oauth_access_token_encrypted or "")
    if not access_token:
        raise EmailTransportError("OAuth access token missing — reconnect account")

    if account.provider == EmailProvider.gmail_oauth:
        host, port = "smtp.gmail.com", 587
    else:
        host, port = "smtp.office365.com", 587

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((account.display_name or account.email_address, account.email_address))
    msg["To"] = to_email
    msg["Message-ID"] = make_msgid()
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    auth_string = f"user={account.email_address}\x01auth=Bearer {access_token}\x01\x01"
    auth_b64 = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.docmd("AUTH", "XOAUTH2 " + auth_b64)
        server.sendmail(account.email_address, [to_email], msg.as_string())

    return msg["Message-ID"]


def send_email(
    account: EmailAccount,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> str:
    try:
        return _smtp_send(account, to_email, subject, body_text, body_html, in_reply_to, references)
    except Exception as exc:
        logger.exception("Email send failed for account %s", account.id)
        raise EmailTransportError(str(exc)) from exc


def fetch_inbox_messages(account: EmailAccount, since_uid: int = 0, limit: int = 50) -> list[dict]:
    creds = decrypt_json(account.encrypted_credentials or "")
    password = creds.get("password")
    imap_host = account.imap_host
    imap_port = account.imap_port or 993

    if account.provider == EmailProvider.gmail_oauth:
        imap_host = imap_host or "imap.gmail.com"
    elif account.provider == EmailProvider.outlook_oauth:
        imap_host = imap_host or "outlook.office365.com"
    elif account.provider == EmailProvider.smtp:
        imap_host = imap_host or account.smtp_host

    if not imap_host:
        return []

    if account.provider in (EmailProvider.gmail_oauth, EmailProvider.outlook_oauth):
        return _fetch_oauth_imap(account, imap_host, imap_port, limit)

    if not password:
        return []

    messages: list[dict] = []
    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(account.email_address, password)
        mail.select("INBOX")
        _, data = mail.search(None, "UNSEEN")
        ids = (data[0] or b"").split()[-limit:]
        for msg_id in ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)
            messages.append(_parse_email_message(parsed))
        mail.logout()
    except Exception as exc:
        logger.warning("IMAP sync failed for account %s: %s", account.id, exc)
    return messages


def _fetch_oauth_imap(account: EmailAccount, host: str, port: int, limit: int) -> list[dict]:
    access_token = decrypt_secret(account.oauth_access_token_encrypted or "")
    if not access_token:
        return []

    messages: list[dict] = []
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        auth_string = f"user={account.email_address}\x01auth=Bearer {access_token}\x01\x01"
        mail.authenticate("XOAUTH2", lambda _: auth_string.encode())
        mail.select("INBOX")
        _, data = mail.search(None, "UNSEEN")
        ids = (data[0] or b"").split()[-limit:]
        for msg_id in ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            parsed = email.message_from_bytes(raw)
            messages.append(_parse_email_message(parsed))
        mail.logout()
    except Exception as exc:
        logger.warning("OAuth IMAP sync failed for account %s: %s", account.id, exc)
    return messages


def _parse_email_message(parsed: email.message.Message) -> dict:
    subject = parsed.get("Subject", "")
    from_email = parsed.get("From", "")
    to_email = parsed.get("To", "")
    message_id = parsed.get("Message-ID", "")
    in_reply_to = parsed.get("In-Reply-To", "")
    references = parsed.get("References", "")

    body_text = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                payload = part.get_payload(decode=True)
                if payload:
                    body_text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
    else:
        payload = parsed.get_payload(decode=True)
        if payload:
            body_text = payload.decode(parsed.get_content_charset() or "utf-8", errors="replace")

    return {
        "subject": subject,
        "from_email": from_email,
        "to_email": to_email,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "body_text": body_text.strip(),
    }


def refresh_oauth_token(account: EmailAccount) -> bool:
    from app.core.config import get_settings

    settings = get_settings()
    refresh_token = decrypt_secret(account.oauth_refresh_token_encrypted or "")
    if not refresh_token:
        return False

    if account.provider == EmailProvider.gmail_oauth:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return False
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    elif account.provider == EmailProvider.outlook_oauth:
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            return False
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        data = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/SMTP.Send offline_access",
        }
    else:
        return False

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(token_url, data=data)
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return False

    from datetime import UTC, datetime, timedelta
    from app.utils.secret_encryption import encrypt_secret

    account.oauth_access_token_encrypted = encrypt_secret(payload.get("access_token", ""))
    expires_in = int(payload.get("expires_in", 3600))
    account.oauth_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    if payload.get("refresh_token"):
        account.oauth_refresh_token_encrypted = encrypt_secret(payload["refresh_token"])
    return True
