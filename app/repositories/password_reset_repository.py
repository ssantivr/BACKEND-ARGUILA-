from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        self.session.add(token)
        self.session.commit()
        return token

    def get_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        return self.session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )

    def delete_for_user(self, user_id: int) -> None:
        self.session.execute(
            delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        self.session.commit()

    def delete_expired(self, now: datetime) -> None:
        self.session.execute(
            delete(PasswordResetToken).where(PasswordResetToken.expires_at <= now)
        )
        self.session.commit()
