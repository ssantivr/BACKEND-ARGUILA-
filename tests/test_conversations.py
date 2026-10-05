import pytest
from fastapi.testclient import TestClient

from app.ai import get_optional_assistant
from app.database import get_session
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
    app.dependency_overrides[get_optional_assistant] = lambda: fake
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
    assert (answer["role"], answer["content"], answer["source"]) == ("assistant", "reply 1", "ai")

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
        json={"name": "Brick", "unit": "u", "quantity": 1000, "unit_cost": 0.3},
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
    assert '"total_cost": 1105.0' in system and '"total_cost": 300.0' in system
    assert '"materials_total_cost": 1405.0' in system
    assert '"most_expensive_material": "Concrete"' in system
    assert system.index("Concrete") < system.index("Brick")
    assert messages == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply 1"},
        {"role": "user", "content": "second"},
    ]


def test_rules_answer_when_the_assistant_fails(client, conversation_id, assistant):
    assistant.error = AIUnavailableError("Could not reach the AI assistant")

    response = send(client, conversation_id, "hola")

    assert response.status_code == 201
    question, answer = response.json()
    assert question["source"] is None
    assert (answer["role"], answer["source"]) == ("assistant", "rules")
    assert "Demo House" in answer["content"]
    assert len(client.get(f"/conversations/{conversation_id}").json()["messages"]) == 2


def test_rules_answer_when_the_assistant_is_not_configured(client, project_id, conversation_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={
            "name": "Main Lot",
            "area_m2": 450,
            "length_m": 30,
            "slope_percent": 10,
            "soil_type": "clay",
        },
    )
    client.post(
        f"/projects/{project_id}/materials",
        json={"name": "Concrete", "unit": "m3", "quantity": 10, "unit_cost": 110.5},
    )

    terrain = send(client, conversation_id, "¿Cómo es la pendiente del terreno?").json()[1]
    materials = send(client, conversation_id, "¿Cuánto cuestan los materiales?").json()[1]
    drawings = send(client, conversation_id, "¿Qué planos hay?").json()[1]

    assert terrain["source"] == materials["source"] == drawings["source"] == "rules"
    assert "Main Lot" in terrain["content"] and "10 %" in terrain["content"]
    assert "3 m" in terrain["content"] and "arcilloso" in terrain["content"]
    assert "1.105,00" in materials["content"] and "Concrete" in materials["content"]
    assert "Aún no hay planos" in drawings["content"]


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


def test_assistant_status_reports_who_answers(client):
    assert client.get("/assistant/status").status_code == 401

    register(client)

    assert client.get("/assistant/status").json() == {"provider": "rules", "model": None}


def test_the_database_is_released_while_the_assistant_answers(client, conversation_id, assistant):
    opened = []
    provide_session = app.dependency_overrides[get_session]
    in_transaction = []

    def tracked_session():
        for session in provide_session():
            opened.append(session)
            yield session

    def reply(system, messages):
        in_transaction.append(opened[-1].in_transaction())
        return "ok"

    app.dependency_overrides[get_session] = tracked_session
    assistant.reply = reply

    assert send(client, conversation_id).status_code == 201
    assert in_transaction == [False]
