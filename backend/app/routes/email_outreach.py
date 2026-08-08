from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.repositories.email_outreach_repository import EmailOutreachRepository
from app.schemas.email_outreach import (
    ActivityLogResponse,
    AgentActionResponse,
    AgentStatusResponse,
    AiReplyDraftActionRequest,
    AiReplyDraftResponse,
    CampaignLaunchResponse,
    ChatAiReplyRequest,
    ChatMessageResponse,
    ChatStartRequest,
    ChatThreadDetailResponse,
    ChatThreadResponse,
    ConversationResponse,
    EmailAccountResponse,
    EmailOutreachCampaignCreateRequest,
    EmailOutreachCampaignResponse,
    EmailOutreachCampaignUpdateRequest,
    EmailOutreachDashboardResponse,
    EmailOutreachSettingsResponse,
    EmailOutreachSettingsUpdateRequest,
    EmailVerificationResponse,
    ManualLeadOutreachResponse,
    NotificationResponse,
    OAuthStartResponse,
    OutreachEmailResponse,
    OutreachEmailUpdateRequest,
    SmtpAccountCreateRequest,
    TimelineEventResponse,
)
from app.services.email_outreach.agent import AiOutreachAgent
from app.services.email_outreach.campaign import EmailOutreachCampaignService
from app.services.email_outreach.notifications import NotificationService
from app.services.email_outreach.oauth import OAuthService
from app.services.email_outreach.reply import ReplyService
from app.services.email_outreach.service import EmailOutreachService

router = APIRouter(prefix="/api/email-outreach", tags=["email-outreach"])


@router.get("/dashboard", response_model=EmailOutreachDashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return EmailOutreachService(db).get_dashboard(current_user)
    except Exception as exc:
        from sqlalchemy.exc import OperationalError

        from app.utils.sqlite_retry import is_sqlite_locked_error

        if isinstance(exc, OperationalError) and is_sqlite_locked_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Server is busy. Please try again in a few seconds.",
            ) from exc
        raise


@router.get("/settings", response_model=EmailOutreachSettingsResponse)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).get_settings(current_user)


@router.put("/settings", response_model=EmailOutreachSettingsResponse)
def update_settings(
    data: EmailOutreachSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).update_settings(current_user, data)


@router.get("/accounts", response_model=list[EmailAccountResponse])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).list_accounts(current_user)


@router.post("/accounts/smtp", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
def connect_smtp(
    data: SmtpAccountCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).connect_smtp(current_user, data)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmailOutreachService(db).delete_account(current_user, account_id)


@router.post("/accounts/{account_id}/default", response_model=EmailAccountResponse)
def set_default_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).set_default_account(current_user, account_id)


@router.get("/oauth/google/start", response_model=OAuthStartResponse)
def start_google_oauth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = EmailOutreachService(db).start_google_oauth(current_user)
    return OAuthStartResponse(authorization_url=url)


@router.get("/oauth/google/callback")
def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    redirect_url = OAuthService(EmailOutreachRepository(db)).handle_google_callback(code, state)
    return RedirectResponse(url=redirect_url)


@router.get("/oauth/microsoft/start", response_model=OAuthStartResponse)
def start_microsoft_oauth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    url = EmailOutreachService(db).start_microsoft_oauth(current_user)
    return OAuthStartResponse(authorization_url=url)


@router.get("/oauth/microsoft/callback")
def microsoft_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    redirect_url = OAuthService(EmailOutreachRepository(db)).handle_microsoft_callback(code, state)
    return RedirectResponse(url=redirect_url)


@router.post("/verify", response_model=EmailVerificationResponse)
def verify_email(
    email: str = Query(...),
    website: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).verify_email(email, website)


@router.get("/campaigns", response_model=list[EmailOutreachCampaignResponse])
def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachCampaignService(db).list_campaigns(current_user)


@router.post("/campaigns", response_model=EmailOutreachCampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: EmailOutreachCampaignCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachCampaignService(db).create_campaign(current_user, data)


@router.get("/campaigns/{campaign_id}", response_model=EmailOutreachCampaignResponse)
def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachCampaignService(db).get_campaign(current_user, campaign_id)


@router.put("/campaigns/{campaign_id}", response_model=EmailOutreachCampaignResponse)
def update_campaign(
    campaign_id: int,
    data: EmailOutreachCampaignUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachCampaignService(db).update_campaign(current_user, campaign_id, data)


@router.post("/campaigns/{campaign_id}/launch", response_model=CampaignLaunchResponse)
def launch_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachCampaignService(db).launch_campaign(current_user, campaign_id)


@router.get("/emails", response_model=list[OutreachEmailResponse])
def list_emails(
    campaign_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = EmailOutreachRepository(db)
    rows = repo.list_outreach_emails(
        current_user.id, campaign_id=campaign_id, status=status_filter, limit=200
    )
    return [OutreachEmailResponse.model_validate(r) for r in rows]


@router.put("/emails/{email_id}", response_model=OutreachEmailResponse)
def update_email(
    email_id: int,
    data: OutreachEmailUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = EmailOutreachRepository(db)
    row = repo.get_outreach_email(current_user.id, email_id)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Email not found")
    updated = repo.update_outreach_email(row, data.model_dump(exclude_unset=True))
    return OutreachEmailResponse.model_validate(updated)


@router.post("/emails/{email_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
def approve_email(
    email_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    EmailOutreachCampaignService(db).approve_email(current_user, email_id)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = EmailOutreachRepository(db)
    return [ConversationResponse.model_validate(c) for c in repo.list_conversations(current_user.id)]


@router.get("/chat/threads", response_model=list[ChatThreadResponse])
def list_chat_threads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.email_outreach.chat_service import EmailChatService

    return [ChatThreadResponse(**t) for t in EmailChatService(db).list_threads(current_user)]


@router.get("/chat/leads/{lead_id}", response_model=ChatThreadDetailResponse)
def get_chat_for_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.email_outreach.chat_service import EmailChatService

    data = EmailChatService(db).get_messages(current_user, lead_id)
    return ChatThreadDetailResponse(
        lead_id=data["lead_id"],
        conversation_id=data["conversation_id"],
        lead_name=data["lead_name"],
        lead_email=data["lead_email"],
        subject=data["subject"],
        status=data["status"],
        messages=[ChatMessageResponse(**m) for m in data["messages"]],
        is_online=bool(data.get("is_online")),
        last_seen_at=data.get("last_seen_at"),
    )


@router.post("/chat/leads/{lead_id}/reply", response_model=ChatMessageResponse)
async def reply_in_chat(
    lead_id: int,
    subject: str = Form(...),
    body: str = Form(""),
    account_id: int | None = Form(None),
    files: list[UploadFile] | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a chat reply — optional file / image / voice attachments (email)."""
    from app.services.email_outreach.chat_service import EmailChatService

    attachments: list[tuple[str, bytes, str]] = []
    for upload in files or []:
        raw = await upload.read()
        if not raw:
            continue
        if len(raw) > 12 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large (max 12MB): {upload.filename}",
            )
        if len(attachments) >= 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 8 attachments per message",
            )
        name = (upload.filename or "attachment").strip() or "attachment"
        ctype = (upload.content_type or "application/octet-stream").strip()
        attachments.append((name, raw, ctype))

    if not (body or "").strip() and not attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Write a message or attach a file",
        )

    result = EmailChatService(db).send_reply(
        current_user,
        lead_id,
        subject=subject,
        body=body or "",
        account_id=account_id,
        attachments=attachments or None,
    )
    return ChatMessageResponse(**result)


@router.post("/chat/leads/{lead_id}/ai-reply", response_model=ChatMessageResponse)
def ai_reply_in_chat(
    lead_id: int,
    data: ChatAiReplyRequest = ChatAiReplyRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a reply with AI from thread context and send it immediately."""
    from app.services.email_outreach.chat_service import EmailChatService

    result = EmailChatService(db).send_ai_reply(
        current_user, lead_id, hint=data.hint, account_id=data.account_id
    )
    return ChatMessageResponse(**result)


@router.post("/chat/sync-inbox")
def sync_chat_inbox(
    focus_email: str | None = Query(
        None, description="Prioritize pulling replies from this sender (open chat)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pull inbox replies into Chat (IMAP). Call from Chat page Sync button."""
    from app.services.email_outreach.sync import InboxSyncService

    result = InboxSyncService(db).sync_all_for_user(
        current_user.id, focus_email=focus_email
    )
    return {
        "ok": True,
        "synced": result.get("synced", 0),
        "matched_replies": result.get("matched_replies", 0),
        "new_replies": result.get("new_replies", 0),
    }


@router.post("/chat/start", response_model=ChatThreadDetailResponse)
def start_manual_chat(
    data: ChatStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add any email/Gmail contact and send the first message (WhatsApp-style new chat)."""
    from app.services.email_outreach.chat_service import EmailChatService

    detail = EmailChatService(db).start_manual_chat(
        current_user,
        email=data.email,
        name=data.name,
        subject=data.subject,
        body=data.body,
        account_id=data.account_id,
    )
    return ChatThreadDetailResponse(
        lead_id=detail["lead_id"],
        conversation_id=detail["conversation_id"],
        lead_name=detail["lead_name"],
        lead_email=detail["lead_email"],
        subject=detail["subject"],
        status=detail["status"],
        messages=[ChatMessageResponse(**m) for m in detail["messages"]],
        is_online=bool(detail.get("is_online")),
        last_seen_at=detail.get("last_seen_at"),
    )


@router.delete("/chat/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_thread(
    lead_id: int,
    delete_lead: bool = Query(False, description="Also delete the contact/lead"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a chat thread from the sidebar. Optionally delete the contact/lead too."""
    from app.services.email_outreach.chat_service import EmailChatService

    EmailChatService(db).delete_thread(current_user, lead_id, delete_lead=delete_lead)


@router.get("/ai-drafts", response_model=list[AiReplyDraftResponse])
def list_ai_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = EmailOutreachRepository(db)
    return [AiReplyDraftResponse.model_validate(d) for d in repo.list_ai_drafts(current_user.id)]


@router.post("/ai-drafts/{draft_id}/action", response_model=AiReplyDraftResponse)
def ai_draft_action(
    draft_id: int,
    data: AiReplyDraftActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = EmailOutreachRepository(db)
    draft = repo.get_ai_draft(current_user.id, draft_id)
    if not draft:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Draft not found")

    if data.action == "reject":
        from app.models.email_outreach import AiReplyDraftStatus
        draft.status = AiReplyDraftStatus.rejected
        db.commit()
    elif data.action in ("approve", "edit"):
        ReplyService(db).approve_draft(
            current_user.id,
            draft_id,
            edit_subject=data.draft_subject,
            edit_body=data.draft_body,
        )
        db.refresh(draft)

    return AiReplyDraftResponse.model_validate(draft)


@router.post("/leads/{lead_id}/send", response_model=ManualLeadOutreachResponse)
def send_lead_outreach(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AiOutreachAgent(db).manual_send_to_lead(current_user, lead_id)
    return ManualLeadOutreachResponse(**result)


@router.get("/timeline/{lead_id}", response_model=list[TimelineEventResponse])
def lead_timeline(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return EmailOutreachService(db).get_lead_timeline(current_user, lead_id)


@router.get("/agent/status", response_model=AgentStatusResponse)
def agent_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AiOutreachAgent(db).get_agent_status(current_user)


@router.post("/agent/start", response_model=AgentActionResponse)
def start_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AiOutreachAgent(db).start_agent(current_user)
    return AgentActionResponse(**result)


@router.post("/agent/stop", response_model=AgentActionResponse)
def stop_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AiOutreachAgent(db).stop_agent(current_user)
    return AgentActionResponse(status=result["status"], message=result["message"])


@router.post("/agent/pause", response_model=AgentActionResponse)
def pause_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AiOutreachAgent(db).pause_agent(current_user)
    return AgentActionResponse(status=result["status"], message=result["message"])


@router.post("/agent/resume", response_model=AgentActionResponse)
def resume_agent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = AiOutreachAgent(db).resume_agent(current_user)
    return AgentActionResponse(status=result["status"], message=result["message"])


@router.get("/agent/activity", response_model=list[ActivityLogResponse])
def agent_activity(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = AiOutreachAgent(db).list_activity(current_user.id, limit=limit)
    return [ActivityLogResponse.model_validate(log) for log in logs]


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = NotificationService(db).list_recent(current_user.id, limit=limit)
    return [NotificationResponse.model_validate(n) for n in rows]


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    NotificationService(db).mark_read(current_user.id, notification_id)


@router.post("/notifications/lead/{lead_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_lead_notifications_read(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread outreach notifications for a lead as read (e.g. when opening chat)."""
    NotificationService(db).mark_read_for_lead(current_user.id, lead_id)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    NotificationService(db).mark_all_read(current_user.id)
