"""Clean stored email/chat text for display — body only, no subject/JSON wrapper."""

from __future__ import annotations

import json
import re


def _strip_quoted_email(text: str) -> str:
    cut_patterns = [
        r"\nOn\s+[^\n]+wrote:\s*\n",
        r"\nOn\s+[^\n]+<[^>]+>\s*wrote:\s*\n",
        r"\n-{2,}\s*Original Message\s*-{2,}",
        r"\nFrom:\s*[^\n]+\nSent:\s*[^\n]+",
        r"\n_{5,}\n",
        r"\nBegin forwarded message:\s*\n",
    ]
    for pattern in cut_patterns:
        idx = re.search(pattern, text, flags=re.I)
        if idx and idx.start() > 0:
            text = text[: idx.start()]
            break
    lines = [ln for ln in text.split("\n") if not re.match(r"^\s*>", ln)]
    text = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _try_parse_json_blob(text: str) -> dict | None:
    blob = text.strip()
    if not blob:
        return None
    candidates = [blob]
    if not blob.startswith("{"):
        candidates.append("{" + blob + "}")
        candidates.append("{" + blob.rstrip(",") + "}")
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def extract_subject_and_body(raw: str | None) -> tuple[str | None, str]:
    """Return (optional embedded subject, clean body text)."""
    if not raw or not str(raw).strip():
        return None, ""

    text = str(raw).replace("\r\n", "\n").replace("\u202f", " ").strip()

    data = _try_parse_json_blob(text)
    if data:
        subj = str(data.get("subject") or data.get("draft_subject") or "").strip() or None
        body = str(data.get("body") or data.get("draft_body") or data.get("message") or "").strip()
        if body:
            return subj, _strip_quoted_email(body)

    # Partial LLM JSON stored as plain text: "subject": "...", "body": "..."
    subj_match = re.search(
        r'"subject"\s*:\s*"((?:\\.|[^"\\])*)"',
        text,
        re.I | re.S,
    )
    body_match = re.search(
        r'"body"\s*:\s*"((?:\\.|[^"\\])*)"',
        text,
        re.I | re.S,
    )
    if body_match:
        body = body_match.group(1).replace("\\n", "\n").replace('\\"', '"').strip()
        subj = subj_match.group(1).replace('\\"', '"').strip() if subj_match else None
        return subj, _strip_quoted_email(body)

    # Line-based Subject: / body fallback
    if re.match(r'^"subject"\s*:', text, re.I):
        lines = text.split("\n")
        subj = None
        body_lines: list[str] = []
        in_body = False
        for line in lines:
            if re.match(r'^\s*"subject"\s*:', line, re.I):
                m = re.search(r'"subject"\s*:\s*"([^"]*)"', line, re.I)
                if m:
                    subj = m.group(1).strip()
                continue
            if re.match(r'^\s*"body"\s*:\s*"?', line, re.I):
                in_body = True
                rest = re.sub(r'^\s*"body"\s*:\s*"?', "", line, flags=re.I)
                rest = rest.rstrip('",')
                if rest:
                    body_lines.append(rest)
                continue
            if in_body:
                body_lines.append(line.rstrip('",'))
        body = "\n".join(body_lines).strip()
        if body:
            return subj, _strip_quoted_email(body)

    return None, _strip_quoted_email(text)


def clean_chat_display_body(raw: str | None, *, fallback_subject: str | None = None) -> str:
    """Message text only — for chat bubbles."""
    _subj, body = extract_subject_and_body(raw)
    if body:
        return body
    if fallback_subject and raw:
        # Drop a leading subject line if it duplicates the email subject field
        first = raw.strip().split("\n", 1)[0]
        if first.lower().startswith("subject:"):
            return _strip_quoted_email(raw.split("\n", 1)[-1].strip())
    return _strip_quoted_email(raw or "")
