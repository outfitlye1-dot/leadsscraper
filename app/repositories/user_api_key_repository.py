from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user_api_key import ApiKeyStatus, ApiProvider, UserApiKey


class UserApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, user_id: int, provider: ApiProvider | None = None) -> list[UserApiKey]:
        query = self.db.query(UserApiKey).filter(UserApiKey.user_id == user_id)
        if provider:
            query = query.filter(UserApiKey.provider == provider)
        return query.order_by(UserApiKey.priority.asc(), UserApiKey.id.asc()).all()

    def get_by_id(self, user_id: int, key_id: int) -> UserApiKey | None:
        return (
            self.db.query(UserApiKey)
            .filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id)
            .first()
        )

    def get_active_keys(self, user_id: int, provider: ApiProvider) -> list[UserApiKey]:
        return (
            self.db.query(UserApiKey)
            .filter(
                UserApiKey.user_id == user_id,
                UserApiKey.provider == provider,
                UserApiKey.status == ApiKeyStatus.active,
            )
            .order_by(UserApiKey.priority.asc(), UserApiKey.id.asc())
            .all()
        )

    def next_priority(self, user_id: int, provider: ApiProvider) -> int:
        keys = self.list_by_user(user_id, provider)
        if not keys:
            return 0
        return max(k.priority for k in keys) + 1

    def create(self, user_id: int, data: dict) -> UserApiKey:
        row = UserApiKey(user_id=user_id, **data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def bulk_create(self, user_id: int, rows: list[dict]) -> list[UserApiKey]:
        created = [UserApiKey(user_id=user_id, **row) for row in rows]
        self.db.add_all(created)
        self.db.commit()
        for row in created:
            self.db.refresh(row)
        return created

    def update(self, row: UserApiKey, data: dict) -> UserApiKey:
        for key, value in data.items():
            if value is not None:
                setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, row: UserApiKey) -> None:
        self.db.delete(row)
        self.db.commit()

    def record_success(self, row: UserApiKey) -> None:
        row.usage_count += 1
        row.last_used_at = datetime.now(UTC)
        row.last_error = None
        self.db.commit()

    def mark_exhausted(self, row: UserApiKey, error: str) -> None:
        row.status = ApiKeyStatus.exhausted
        row.last_error = error[:500]
        row.updated_at = datetime.now(UTC)
        self.db.commit()

    def reset_exhausted(self, user_id: int, provider: ApiProvider | None = None) -> int:
        query = self.db.query(UserApiKey).filter(
            UserApiKey.user_id == user_id,
            UserApiKey.status == ApiKeyStatus.exhausted,
        )
        if provider:
            query = query.filter(UserApiKey.provider == provider)
        count = 0
        for row in query.all():
            row.status = ApiKeyStatus.active
            row.last_error = None
            count += 1
        self.db.commit()
        return count
