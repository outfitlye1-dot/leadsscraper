from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.message import (
    MessageGenerateRequest,
    MessageGenerateResponse,
    ScrapeSuggestRequest,
    ScrapeSuggestResponse,
    SearchQueryOptimizeRequest,
    SearchQueryOptimizeResponse,
)
from app.services.groq_service import GroqService
from app.services.message_service import MessageService
from app.services.scrape_suggest_service import ScrapeSuggestService

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post(
    "/generate",
    response_model=MessageGenerateResponse,
    summary="Generate AI outreach message",
    description="Generate personalized WhatsApp, email, LinkedIn, or follow-up message using Groq AI.",
    responses={
        400: {"description": "CV profile required"},
        401: {"description": "Not authenticated"},
        404: {"description": "Lead or campaign not found"},
    },
)
def generate_message(
    data: MessageGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageGenerateResponse:
    return MessageService(db).generate_message(current_user, data)


@router.post(
    "/optimize-search-query",
    response_model=SearchQueryOptimizeResponse,
    summary="AI fix & suggest internet search query",
    responses={
        401: {"description": "Not authenticated"},
    },
)
def optimize_search_query(
    data: SearchQueryOptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchQueryOptimizeResponse:
    groq = GroqService(db, current_user.id)
    result = groq.optimize_search_query(data.query, data.location)
    return SearchQueryOptimizeResponse(**result)


@router.post(
    "/suggest-scrape",
    response_model=ScrapeSuggestResponse,
    summary="Brain-based scrape query suggestions (Groq AI)",
    description="Read AI Brain profile and suggest keywords and search queries. Location is set manually by the user.",
    responses={
        400: {"description": "No Brain profile or missing location for daily scrape"},
        401: {"description": "Not authenticated"},
    },
)
def suggest_scrape_queries(
    data: ScrapeSuggestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScrapeSuggestResponse:
    return ScrapeSuggestService(db).suggest(current_user, data)
