import pytest
from fastapi.testclient import TestClient

from app.ai import get_assistant
from app.errors import AIUnavailableError
from app.main import app
from tests.helpers import register


class FakeAssistant:
    def __init__(self):
        self.calls = []
        self.error = None

    def reply(self, system, messages):
        self.calls.append((system, messages))

        if self.error is not None:
            raise self.error

        return f"reply {len(self.calls)}"


@pytest.fixture
def assistant(client):
    fake = FakeAssistant()
    app.dependency_overrides[get_assistant] = lambda: fake
    return fake


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post("/projects", json={"name": "Demo House", "location": "Quito"})
    return project.json()["id"]


@pytest.fixture
def conversation_id(client, project_id):
    response = client.post(f"/projects/{project_id}/conversations", json={})
    assert response.status_code == 201
    return response.json()["id"]


def send(client, conversation_id, content="¿Qué cimentación conviene?"):
    return client.post(f"/conversations/{conversation_id}/messages", json={"content": content})


def test_create_and_list_conversations(client, project_id):
    created = client.post(
        f"/projects/{project_id}/conversations", json={"title": "Cimentación"}
    ).json()

    assert created["title"] == "Cimentación"
    assert created["project_id"] == project_id
    assert client.get(f"/projects/{project_id}/conversations").json() == [created]

    detail = client.get(f"/conversations/{created['id']}").json()
    assert detail["messages"] == []


def test_send_message_stores_question_and_answer(client, conversation_id, assistant):
    response = send(client, conversation_id)

    assert response.status_code == 201
    question, answer = response.json()
    assert (question["role"], question["content"]) == ("user", "¿Qué cimentación conviene?")
    assert (answer["role"], answer["content"]) == ("assistant", "reply 1")

    detail = client.get(f"/conversations/{conversation_id}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["title"] == "¿Qué cimentación conviene?"


def test_assistant_receives_project_data_and_full_history(
    client, project_id, conversation_id, assistant
):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Main Lot", "area_m2": 450, "slope_percent": 22.5, "soil_type": "clay"},
    )
    client.post(
        f"/projects/{project_id}/materials",
        json={"name": "Concrete", "unit": "m3", "quantity": 10, "unit_cost": 110.5},
    )

    send(client, conversation_id, "first")
    send(client, conversation_id, "second")

    system, messages = assistant.calls[1]
    assert "Demo House" in system and "Quito" in system
    assert "Main Lot" in system and "22.5" in system and "clay" in system
    assert "Concrete" in system and "1105.0" in system
    assert messages == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply 1"},
        {"role": "user", "content": "second"},
    ]


def test_nothing_is_stored_when_the_assistant_fails(client, conversation_id, assistant):
    assistant.error = AIUnavailableError("Could not reach the AI assistant")

    response = send(client, conversation_id)

    assert response.status_code == 503
    assert response.json() == {"detail": "Could not reach the AI assistant"}
    assert client.get(f"/conversations/{conversation_id}").json()["messages"] == []


def test_unconfigured_assistant_returns_503(client, conversation_id, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    response = send(client, conversation_id)

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


@pytest.mark.parametrize("content", ["", "x" * 4001])
def test_invalid_message_is_rejected(client, conversation_id, assistant, content):
    assert send(client, conversation_id, content).status_code == 422
    assert assistant.calls == []


def test_delete_conversation(client, conversation_id, assistant):
    send(client, conversation_id)

    assert client.delete(f"/conversations/{conversation_id}").status_code == 204
    assert client.get(f"/conversations/{conversation_id}").status_code == 404
    assert send(client, conversation_id).status_code == 404


def test_conversations_are_private_to_their_owner(client, project_id, conversation_id, assistant):
    send(client, conversation_id)

    intruder = TestClient(app)
    register(intruder, name="Eve", email="eve@example.com")

    assert intruder.get(f"/projects/{project_id}/conversations").status_code == 404
    assert intruder.post(f"/projects/{project_id}/conversations", json={}).status_code == 404
    assert intruder.get(f"/conversations/{conversation_id}").status_code == 404
    assert send(intruder, conversation_id).status_code == 404
    assert intruder.delete(f"/conversations/{conversation_id}").status_code == 404
    assert len(assistant.calls) == 1


def test_requires_authentication(client):
    assert client.get("/projects/1/conversations").status_code == 401
    assert client.get("/conversations/1").status_code == 401
    assert client.post("/conversations/1/messages", json={"content": "hi"}).status_code == 401
