import pytest

from app.services import login_limiter
from app.services.login_limiter import reset_request_limiter
from app.services.undo_history import undo_history
from tests.helpers import PASSWORD, register


@pytest.fixture
def database_state(monkeypatch):
    monkeypatch.setenv("STATE_STORAGE", "database")


def forget_memory():
    undo_history.clear()
    login_limiter.login_limiter.clear()
    reset_request_limiter.clear()


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


def wrong_login(client):
    return client.post("/auth/login", json={"email": "ana@example.com", "password": "wrong-pass"})


def test_failed_logins_are_counted_across_instances(client, database_state):
    register(client)

    for _ in range(login_limiter.MAX_FAILED_ATTEMPTS):
        assert wrong_login(client).status_code == 401
        forget_memory()

    assert wrong_login(client).status_code == 429
    forget_memory()
    assert wrong_login(client).status_code == 429


def test_the_block_ends_when_the_window_passes(client, database_state, monkeypatch):
    clock = [5000.0]
    monkeypatch.setattr(login_limiter, "now", lambda: clock[0])
    monkeypatch.setattr(login_limiter, "wall_clock", lambda: clock[0] + 1_000_000)
    register(client)

    for _ in range(login_limiter.MAX_FAILED_ATTEMPTS):
        wrong_login(client)

    forget_memory()
    assert wrong_login(client).status_code == 429

    clock[0] += login_limiter.WINDOW_SECONDS + 1
    forget_memory()
    assert wrong_login(client).status_code == 401


def test_a_correct_login_clears_the_stored_failures(client, database_state):
    register(client)

    for _ in range(login_limiter.MAX_FAILED_ATTEMPTS - 1):
        wrong_login(client)

    forget_memory()
    correct = client.post("/auth/login", json={"email": "ana@example.com", "password": PASSWORD})
    assert correct.status_code == 200

    forget_memory()
    for _ in range(login_limiter.MAX_FAILED_ATTEMPTS - 1):
        assert wrong_login(client).status_code == 401


def test_undo_and_redo_work_across_instances(client, project_id, database_state):
    terrain = client.post(
        f"/projects/{project_id}/terrains",
        json={
            "name": "Lote 14",
            "area_m2": 200.5,
            "points": [
                {"x_m": 0, "y_m": 0},
                {"x_m": 10, "y_m": 0},
                {"x_m": 10, "y_m": 20.05},
            ],
        },
    ).json()
    material = client.post(
        f"/projects/{project_id}/materials",
        json={"name": "Cemento", "unit": "saco", "quantity": 12.5, "unit_cost": 8.75},
    ).json()

    assert client.delete(f"/terrains/{terrain['id']}").status_code == 204
    assert client.delete(f"/materials/{material['id']}").status_code == 204

    forget_memory()
    listed = client.get(f"/projects/{project_id}/undo").json()
    assert [item["label"] for item in listed] == ["Cemento", "Lote 14"]

    forget_memory()
    assert client.post(f"/projects/{project_id}/undo").json()["label"] == "Cemento"
    forget_memory()
    assert client.post(f"/projects/{project_id}/undo").json()["label"] == "Lote 14"

    restored_material = client.get(f"/projects/{project_id}/materials").json()[0]
    assert restored_material["quantity"] == material["quantity"]
    assert restored_material["unit_cost"] == material["unit_cost"]

    restored_terrain = client.get(f"/projects/{project_id}/terrains").json()[0]
    assert restored_terrain["area_m2"] == terrain["area_m2"]
    assert [(point["x_m"], point["y_m"]) for point in restored_terrain["points"]] == [
        (point["x_m"], point["y_m"]) for point in terrain["points"]
    ]

    forget_memory()
    assert client.post(f"/projects/{project_id}/redo").json()["label"] == "Lote 14"
    forget_memory()
    assert client.get(f"/projects/{project_id}/terrains").json() == []
    assert client.post(f"/projects/{project_id}/undo").json()["label"] == "Lote 14"

    forget_memory()
    assert client.post(f"/projects/{project_id}/redo").json()["label"] == "Lote 14"
    assert client.post(f"/projects/{project_id}/redo").json()["label"] == "Cemento"
    assert client.post(f"/projects/{project_id}/redo").status_code == 404


def test_deleting_the_project_drops_its_stored_history(client, project_id, database_state):
    terrain = client.post(
        f"/projects/{project_id}/terrains", json={"name": "Lote", "area_m2": 100}
    ).json()
    client.delete(f"/terrains/{terrain['id']}")

    assert client.delete(f"/projects/{project_id}").status_code == 204

    again = client.post("/projects", json={"name": "Demo House"}).json()["id"]
    forget_memory()
    assert client.get(f"/projects/{again}/undo").json() == []


def test_memory_is_used_when_the_database_state_is_off(client, project_id):
    terrain = client.post(
        f"/projects/{project_id}/terrains", json={"name": "Lote", "area_m2": 100}
    ).json()
    client.delete(f"/terrains/{terrain['id']}")

    forget_memory()
    assert client.get(f"/projects/{project_id}/undo").json() == []
