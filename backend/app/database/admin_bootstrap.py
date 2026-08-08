import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

LEGACY_ADMIN_EMAIL = "admin@leadgen.local"


def ensure_admin_user(db: Session) -> None:
    settings = get_settings()
    email = settings.ADMIN_EMAIL.strip().lower()
    password = settings.ADMIN_PASSWORD.strip()
    if not email or not password:
        return

    repo = UserRepository(db)
    legacy = repo.get_by_email(LEGACY_ADMIN_EMAIL)
    user = repo.get_by_email(email)

    if legacy and user and legacy.id != user.id:
        repo.delete_user(legacy)
        logger.info("Removed legacy admin account %s (using %s)", LEGACY_ADMIN_EMAIL, email)
        user = repo.get_by_email(email)
    elif legacy and not user:
        legacy.email = email
        legacy.role = UserRole.admin
        legacy.password_hash = get_password_hash(password)
        db.commit()
        logger.info("Migrated legacy admin email to %s", email)
        return

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
