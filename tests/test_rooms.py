import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import register

ROOM = {"name": "Kitchen", "x_m": 1.5, "y_m": 2, "width_m": 4, "depth_m": 3.25}


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


@pytest.fixture
def plan_id(client, project_id):
    return client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()["id"]


def create(client, project_id, plan_id, **overrides):
    return client.post(
        f"/projects/{project_id}/rooms", json={**ROOM, "plan_id": plan_id, **overrides}
    )


def test_rooms_require_authentication(client):
    assert client.get("/projects/1/rooms").status_code == 401


def test_create_and_list_rooms(client, project_id, plan_id):
    response = create(client, project_id, plan_id)

    assert response.status_code == 201
    room = response.json()
    assert room["project_id"] == project_id
    assert room["plan_id"] == plan_id
    assert room["height_m"] == 3
    assert (room["x_m"], room["depth_m"]) == (1.5, 3.25)

    assert client.get(f"/rooms/{room['id']}").json() == room
    assert client.get(f"/projects/{project_id}/rooms").json() == [room]


def test_room_measures_must_be_positive(client, project_id, plan_id):
    assert create(client, project_id, plan_id, width_m=0).status_code == 422
    assert create(client, project_id, plan_id, depth_m=-1).status_code == 422
    assert create(client, project_id, plan_id, height_m=0).status_code == 422
    assert create(client, project_id, plan_id, name="").status_code == 422


def test_room_plan_must_belong_to_the_project(client, project_id, plan_id):
    other_project = client.post("/projects", json={"name": "Tower"}).json()["id"]
    foreign_plan = client.post(f"/projects/{other_project}/plans", json={"title": "Other"}).json()[
        "id"
    ]
    room_id = create(client, project_id, plan_id).json()["id"]

    assert create(client, project_id, foreign_plan).status_code == 404
    assert create(client, project_id, 9999).status_code == 404
    assert client.patch(f"/rooms/{room_id}", json={"plan_id": foreign_plan}).status_code == 404


def test_update_and_delete_room(client, project_id, plan_id):
    room_id = create(client, project_id, plan_id).json()["id"]

    response = client.patch(f"/rooms/{room_id}", json={"name": "Hall", "width_m": 6, "x_m": None})

    assert response.status_code == 200
    assert response.json()["name"] == "Hall"
    assert response.json()["width_m"] == 6
    assert response.json()["x_m"] == 1.5

    assert client.patch(f"/rooms/{room_id}", json={"width_m": 0}).status_code == 422

    assert client.delete(f"/rooms/{room_id}").status_code == 204
    assert client.get(f"/rooms/{room_id}").status_code == 404


def test_rooms_are_hidden_from_other_users(client, project_id, plan_id):
    room_id = create(client, project_id, plan_id).json()["id"]

    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    assert other.get(f"/projects/{project_id}/rooms").status_code == 404
    assert other.get(f"/rooms/{room_id}").status_code == 404
    assert other.patch(f"/rooms/{room_id}", json={"name": "Mine"}).status_code == 404
    assert other.delete(f"/rooms/{room_id}").status_code == 404
    assert create(other, project_id, plan_id).status_code == 404


def test_deleting_a_plan_deletes_its_rooms(client, project_id, plan_id):
    room_id = create(client, project_id, plan_id).json()["id"]

    assert client.delete(f"/plans/{plan_id}").status_code == 204

    assert client.get(f"/rooms/{room_id}").status_code == 404
    assert client.get(f"/projects/{project_id}/rooms").json() == []


def test_deleting_a_project_deletes_its_rooms(client, project_id, plan_id):
    room_id = create(client, project_id, plan_id).json()["id"]

    assert client.delete(f"/projects/{project_id}").status_code == 204

    assert client.get(f"/rooms/{room_id}").status_code == 404
