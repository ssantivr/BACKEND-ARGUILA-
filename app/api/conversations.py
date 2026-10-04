from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.ai import Assistant, get_assistant_status, get_optional_assistant
from app.api.deps import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import (
    AssistantStatus,
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["assistant"])


def get_service(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ConversationService:
    return ConversationService(session, user)


@router.get("/assistant/status", response_model=AssistantStatus)
def assistant_status(
    user: User = Depends(get_current_user),
    current: dict[str, str | None] = Depends(get_assistant_status),
):
    return current


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    project_id: int,
    data: ConversationCreate,
    service: ConversationService = Depends(get_service),
):
    return service.create(project_id, data.title)


@router.get(
    "/projects/{project_id}/conversations", response_model=list[ConversationRead]
)
def list_conversations(
    project_id: int, service: ConversationService = Depends(get_service)
):
    return service.list(project_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int, service: ConversationService = Depends(get_service)
):
    return service.get(conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: int,
    data: MessageCreate,
    service: ConversationService = Depends(get_service),
    assistant: Assistant | None = Depends(get_optional_assistant),
):
    return service.send_message(conversation_id, data.content, assistant)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int, service: ConversationService = Depends(get_service)
):
    service.delete(conversation_id)
    return Response(status_code=204)
