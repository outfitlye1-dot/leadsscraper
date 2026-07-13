from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.user import (
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.otp_service import OtpService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and password.",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
    },
)
def register(data: UserRegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    return AuthService(db).register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login user",
    description="Authenticate user and return JWT access token.",
    responses={
        401: {"description": "Incorrect email or password"},
        422: {"description": "Validation error"},
    },
)
def login(data: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    result = AuthService(db).login(data)
    return TokenResponse(**result)


@router.post(
    "/otp/send",
    response_model=OtpSendResponse,
    summary="Send OTP (login, register, or reset password)",
    responses={
        404: {"description": "Account not found (login)"},
        409: {"description": "Email already registered (register)"},
        429: {"description": "Resend cooldown"},
        503: {"description": "SMTP not configured"},
    },
)
async def send_otp(data: OtpSendRequest, db: Session = Depends(get_db)) -> OtpSendResponse:
    return await OtpService(db).send_otp(data)


@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    summary="Verify OTP and get JWT token",
    responses={
        400: {"description": "Invalid or expired OTP"},
        409: {"description": "Email already registered"},
    },
)
def verify_otp(data: OtpVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    result = OtpService(db).verify_otp(data)
    return TokenResponse(**result)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Return the authenticated user's profile information.",
    responses={401: {"description": "Not authenticated"}},
)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    return AuthService(db).get_user_profile(current_user)
