import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def ensure_admin_user(db: Session) -> None:
    settings = get_settings()
    email = settings.ADMIN_EMAIL.strip().lower()
    password = settings.ADMIN_PASSWORD.strip()
    if not email or not password:
        return

    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if user:
        changed = False
        if user.role != UserRole.admin:
            user.role = UserRole.admin
            changed = True
        if password:
            user.password_hash = get_password_hash(password)
            changed = True
        if changed:
            db.commit()
            logger.info("Admin account updated for %s", email)
        return

    repo.create(
        name=settings.ADMIN_NAME or "Admin",
        email=email,
        password_hash=get_password_hash(password),
        role=UserRole.admin,
    )
    logger.info("Admin account created for %s", email)
