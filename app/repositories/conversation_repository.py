from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIConversation, AIMessage


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, conversation_id: int) -> AIConversation | None:
        return self.session.get(AIConversation, conversation_id)

    def list_by_project(self, project_id: int, user_id: int) -> list[AIConversation]:
        query = select(AIConversation).where(
            AIConversation.project_id == project_id,
            AIConversation.user_id == user_id,
        )
        return list(self.session.scalars(query.order_by(AIConversation.id)))

    def save(self, conversation: AIConversation) -> AIConversation:
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return conversation

    def add_messages(self, messages: list[AIMessage]) -> list[AIMessage]:
        self.session.add_all(messages)
        self.session.commit()

        for message in messages:
            self.session.refresh(message)

        return messages

    def delete(self, conversation: AIConversation) -> None:
        self.session.delete(conversation)
        self.session.commit()
