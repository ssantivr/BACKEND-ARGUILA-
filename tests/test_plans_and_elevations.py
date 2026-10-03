import pytest

from tests.helpers import register

PLAN = {"title": "Ground floor", "level": "0", "scale": "1:100"}
ELEVATION = {"title": "Front facade", "orientation": "north"}


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post(
        "/projects", json={"name": "Demo House"}
    )
    return project.json()["id"]


def create(client, project_id, resource, payload, **overrides):
    return client.post(
        f"/projects/{project_id}/{resource}", json={**payload, **overrides}
    )


def test_create_and_list_plans(client, project_id):
    response = create(client, project_id, "plans", PLAN)

    assert response.status_code == 201
    plan = response.json()
    assert plan["project_id"] == project_id
    assert plan["title"] == "Ground floor"
    assert plan["scale"] == "1:100"
    assert plan["file_id"] is None

    assert client.get(f"/plans/{plan['id']}").json() == plan
    assert client.get(f"/projects/{project_id}/plans").json() == [plan]


def test_update_and_delete_plan(client, project_id):
    plan_id = create(client, project_id, "plans", PLAN).json()["id"]

    response = client.patch(f"/plans/{plan_id}", json={"scale": "1:50", "level": None})

    assert response.status_code == 200
    assert response.json()["scale"] == "1:50"
    assert response.json()["level"] is None
    assert response.json()["title"] == "Ground floor"

    assert client.patch(f"/plans/{plan_id}", json={"title": ""}).status_code == 422

    assert client.delete(f"/plans/{plan_id}").status_code == 204
    assert client.get(f"/plans/{plan_id}").status_code == 404


def test_create_and_filter_elevations(client, project_id):
    response = create(client, project_id, "elevations", ELEVATION)
    create(client, project_id, "elevations", ELEVATION, title="Back", orientation="south")

    assert response.status_code == 201
    elevation = response.json()
    assert elevation["orientation"] == "north"
    assert client.get(f"/elevations/{elevation['id']}").json() == elevation

    def titles(**params):
        response = client.get(f"/projects/{project_id}/elevations", params=params)
        return [e["title"] for e in response.json()]

    assert titles() == ["Front facade", "Back"]
    assert titles(orientation="south") == ["Back"]
    assert titles(orientation="east") == []


def test_invalid_orientation_is_rejected(client, project_id):
    response = create(client, project_id, "elevations", ELEVATION, orientation="up")
    assert response.status_code == 422

    response = client.get(f"/projects/{project_id}/elevations", params={"orientation": "up"})
    assert response.status_code == 422


def test_update_and_delete_elevation(client, project_id):
    elevation_id = create(client, project_id, "elevations", ELEVATION).json()["id"]

    response = client.patch(f"/elevations/{elevation_id}", json={"orientation": "west"})

    assert response.status_code == 200
    assert response.json()["orientation"] == "west"
    assert response.json()["title"] == "Front facade"

    assert client.delete(f"/elevations/{elevation_id}").status_code == 204
    assert client.get(f"/elevations/{elevation_id}").status_code == 404


@pytest.mark.parametrize("resource, payload", [("plans", PLAN), ("elevations", ELEVATION)])
def test_requires_existing_project(client, resource, payload):
    register(client)

    assert create(client, 999, resource, payload).status_code == 404
    assert client.get(f"/projects/999/{resource}").status_code == 404
    assert client.get(f"/{resource}/999").status_code == 404


def test_deleting_project_removes_plans_and_elevations(client, project_id):
    plan_id = create(client, project_id, "plans", PLAN).json()["id"]
    elevation_id = create(client, project_id, "elevations", ELEVATION).json()["id"]

    client.delete(f"/projects/{project_id}")

    assert client.get(f"/plans/{plan_id}").status_code == 404
    assert client.get(f"/elevations/{elevation_id}").status_code == 404
