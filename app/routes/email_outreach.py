from fastapi import APIRouter, Depends, Query, status
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
    ConversationResponse,
    EmailAccountResponse,
    EmailOutreachCampaignCreateRequest,
    EmailOutreachCampaignResponse,
    EmailOutreachCampaignUpdateRequest,
    EmailOutreachDashboardResponse,
    EmailOutreachSettingsResponse,
    EmailOutreachSettingsUpdateRequest,
    EmailVerificationResponse,
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
    return EmailOutreachService(db).get_dashboard(current_user)


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


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    NotificationService(db).mark_all_read(current_user.id)
