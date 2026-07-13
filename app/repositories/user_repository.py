from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email.lower()).first()

    def create(
        self,
        name: str,
        email: str,
        password_hash: str,
        *,
        role: UserRole = UserRole.user,
    ) -> User:
        user = User(name=name, email=email.lower(), password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(
        self,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        query = self.db.query(User)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))
        if role is not None:
            query = query.filter(User.role == role)
        total = query.count()
        users = (
            query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
        )
        return users, total

    def update_user(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete_user(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

    def count_by_role(self) -> dict[str, int]:
        rows = (
            self.db.query(User.role, func.count(User.id))
            .group_by(User.role)
            .all()
        )
        return {role.value: count for role, count in rows}
