from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.models.support_chat import SupportMessage, SupportThread
from app.models.user import User, UserRole


class SupportChatService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_thread(self, user_id: int) -> SupportThread:
        thread = (
            self.db.query(SupportThread)
            .filter(SupportThread.user_id == user_id)
            .first()
        )
        if thread:
            return thread
        thread = SupportThread(user_id=user_id)
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def list_threads_for_admin(self) -> list[dict]:
        threads = (
            self.db.query(SupportThread)
            .options(joinedload(SupportThread.user))
            .order_by(desc(SupportThread.last_message_at), desc(SupportThread.updated_at))
            .all()
        )
        return [self._thread_summary(thread, viewer_role=UserRole.admin) for thread in threads]

    def get_thread_detail(self, viewer: User, target_user_id: int | None = None) -> dict:
        if viewer.role == UserRole.admin:
            if target_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_id is required for admin support chat",
                )
            thread = self.get_or_create_thread(target_user_id)
        else:
            if target_user_id is not None and target_user_id != viewer.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            thread = self.get_or_create_thread(viewer.id)

        user = self.db.query(User).filter(User.id == thread.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        messages = (
            self.db.query(SupportMessage)
            .options(joinedload(SupportMessage.sender))
            .filter(SupportMessage.thread_id == thread.id)
            .order_by(SupportMessage.created_at.asc())
            .all()
        )
        self._mark_read(thread, viewer)
        return {
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
            "user_avatar_url": user.avatar_url,
            "messages": [
                self._message_payload(message, viewer) for message in messages
            ],
            "unread_count": 0,
        }

    def send_message(
        self,
        viewer: User,
        body: str,
        target_user_id: int | None = None,
    ) -> dict:
        text = body.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty",
            )

        if viewer.role == UserRole.admin:
            if target_user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="user_id is required for admin support chat",
                )
            thread = self.get_or_create_thread(target_user_id)
        else:
            if target_user_id is not None and target_user_id != viewer.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
            thread = self.get_or_create_thread(viewer.id)

        now = datetime.now(UTC)
        message = SupportMessage(
            thread_id=thread.id,
            sender_user_id=viewer.id,
            body_text=text,
            created_at=now,
        )
        thread.last_message_at = now
        thread.updated_at = now
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        self.db.refresh(message, attribute_names=["sender"])
        return self._message_payload(message, viewer)

    def delete_message(self, viewer: User, message_id: int) -> None:
        message = (
            self.db.query(SupportMessage)
            .options(joinedload(SupportMessage.thread))
            .filter(SupportMessage.id == message_id)
            .first()
        )
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        thread = message.thread
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

        if viewer.role == UserRole.admin:
            pass
        elif thread.user_id != viewer.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        elif message.sender_user_id != viewer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own messages",
            )

        self.db.delete(message)
        self.db.flush()

        last_message = (
            self.db.query(SupportMessage)
            .filter(SupportMessage.thread_id == thread.id)
            .order_by(desc(SupportMessage.created_at))
            .first()
        )
        thread.last_message_at = last_message.created_at if last_message else None
        thread.updated_at = datetime.now(UTC)
        self.db.commit()

    def _thread_summary(self, thread: SupportThread, *, viewer_role: UserRole) -> dict:
        user = thread.user
        last_message = (
            self.db.query(SupportMessage)
            .filter(SupportMessage.thread_id == thread.id)
            .order_by(desc(SupportMessage.created_at))
            .first()
        )
        return {
            "user_id": thread.user_id,
            "user_name": user.name if user else f"User #{thread.user_id}",
            "user_email": user.email if user else "",
            "user_avatar_url": user.avatar_url if user else None,
            "last_message_at": thread.last_message_at,
            "last_preview": (last_message.body_text[:120] if last_message else None),
            "unread_count": self._unread_count(thread, viewer_role),
        }

    def _unread_count(self, thread: SupportThread, viewer_role: UserRole) -> int:
        last_read = (
            thread.last_read_admin_at
            if viewer_role == UserRole.admin
            else thread.last_read_user_at
        )
        q = self.db.query(SupportMessage).filter(SupportMessage.thread_id == thread.id)
        if viewer_role == UserRole.admin:
            q = q.join(User, SupportMessage.sender_user_id == User.id).filter(
                User.role != UserRole.admin
            )
        else:
            q = q.join(User, SupportMessage.sender_user_id == User.id).filter(
                User.role == UserRole.admin
            )
        if last_read:
            q = q.filter(SupportMessage.created_at > last_read)
        return q.count()

    def _mark_read(self, thread: SupportThread, viewer: User) -> None:
        now = datetime.now(UTC)
        if viewer.role == UserRole.admin:
            thread.last_read_admin_at = now
        else:
            thread.last_read_user_at = now
        thread.updated_at = now
        self.db.commit()

    def _message_payload(self, message: SupportMessage, viewer: User) -> dict:
        sender = message.sender
        sender_role = sender.role.value if sender else "user"
        outbound = message.sender_user_id == viewer.id
        return {
            "id": message.id,
            "direction": "outbound" if outbound else "inbound",
            "body_text": message.body_text,
            "sent_at": message.created_at,
            "sender_name": sender.name if sender else "User",
            "sender_role": sender_role,
            "sender_user_id": message.sender_user_id,
        }
