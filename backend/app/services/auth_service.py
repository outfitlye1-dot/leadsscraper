from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserLoginRequest, UserRegisterRequest, UserResponse
from app.schemas.user_serialize import to_user_response
from app.utils.sqlite_retry import is_sqlite_locked_error, with_sqlite_retry


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def register(self, data: UserRegisterRequest) -> UserResponse:
        def _register() -> UserResponse:
            existing = self.user_repository.get_by_email(data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )

            user = self.user_repository.create(
                name=data.name,
                email=data.email,
                password_hash=get_password_hash(data.password),
            )
            return to_user_response(user, self.db)

        try:
            return with_sqlite_retry(_register)
        except OperationalError as exc:
            if is_sqlite_locked_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Server is busy. Please try again in a few seconds.",
                ) from exc
            raise

    def login(self, data: UserLoginRequest) -> dict:
        def _login() -> dict:
            user = self.user_repository.get_by_email(data.email)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                )
            try:
                password_ok = verify_password(data.password, user.password_hash)
            except (ValueError, TypeError):
                password_ok = False
            if not password_ok:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                )

            access_token = create_access_token(
                data={"sub": str(user.id)},
                expires_delta=timedelta(minutes=60),
            )
            return {"access_token": access_token, "token_type": "bearer"}

        try:
            return with_sqlite_retry(_login)
        except OperationalError as exc:
            if is_sqlite_locked_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Server is busy. Please try again in a few seconds.",
                ) from exc
            raise

    def get_user_profile(self, user: User) -> UserResponse:
        return to_user_response(user, self.db)
