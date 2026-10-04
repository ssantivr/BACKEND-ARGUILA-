import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import register

COLUMN = {
    "kind": "column",
    "name": "C1",
    "x_m": 1.5,
    "y_m": 2,
    "width_m": 0.4,
    "depth_m": 0.4,
    "height_m": 3,
}


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


@pytest.fixture
def plan_id(client, project_id):
    return client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()["id"]


def create(client, project_id, plan_id, **overrides):
    return client.post(
        f"/projects/{project_id}/components", json={**COLUMN, "plan_id": plan_id, **overrides}
    )


def test_components_require_authentication(client):
    assert client.get("/projects/1/components").status_code == 401


def test_create_and_list_components(client, project_id, plan_id):
    response = create(client, project_id, plan_id)

    assert response.status_code == 201
    component = response.json()
    assert component["project_id"] == project_id
    assert component["plan_id"] == plan_id
    assert component["kind"] == "column"
    assert (component["x_m"], component["width_m"]) == (1.5, 0.4)

    assert client.get(f"/components/{component['id']}").json() == component
    assert client.get(f"/projects/{project_id}/components").json() == [component]


def test_filter_components_by_kind(client, project_id, plan_id):
    create(client, project_id, plan_id)
    create(client, project_id, plan_id, kind="wall", name="M1")

    walls = client.get(f"/projects/{project_id}/components", params={"kind": "wall"}).json()

    assert [component["name"] for component in walls] == ["M1"]
    assert (
        client.get(f"/projects/{project_id}/components", params={"kind": "roof"}).status_code == 422
    )


def test_component_data_is_validated(client, project_id, plan_id):
    assert create(client, project_id, plan_id, kind="roof").status_code == 422
    assert create(client, project_id, plan_id, width_m=0).status_code == 422
    assert create(client, project_id, plan_id, depth_m=-1).status_code == 422
    assert create(client, project_id, plan_id, height_m=0).status_code == 422
    assert create(client, project_id, plan_id, name="").status_code == 422


def test_component_plan_must_belong_to_the_project(client, project_id, plan_id):
    other_project = client.post("/projects", json={"name": "Tower"}).json()["id"]
    foreign_plan = client.post(f"/projects/{other_project}/plans", json={"title": "Other"}).json()[
        "id"
    ]
    component_id = create(client, project_id, plan_id).json()["id"]

    assert create(client, project_id, foreign_plan).status_code == 404
    assert create(client, project_id, 9999).status_code == 404
    assert (
        client.patch(f"/components/{component_id}", json={"plan_id": foreign_plan}).status_code
        == 404
    )


def test_update_and_delete_component(client, project_id, plan_id):
    component_id = create(client, project_id, plan_id).json()["id"]

    response = client.patch(
        f"/components/{component_id}", json={"kind": "wall", "width_m": 5, "name": None}
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "wall"
    assert response.json()["width_m"] == 5
    assert response.json()["name"] == "C1"

    assert client.patch(f"/components/{component_id}", json={"kind": "roof"}).status_code == 422

    assert client.delete(f"/components/{component_id}").status_code == 204
    assert client.get(f"/components/{component_id}").status_code == 404


def test_components_are_hidden_from_other_users(client, project_id, plan_id):
    component_id = create(client, project_id, plan_id).json()["id"]

    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    assert other.get(f"/projects/{project_id}/components").status_code == 404
    assert other.get(f"/components/{component_id}").status_code == 404
    assert other.patch(f"/components/{component_id}", json={"name": "Mine"}).status_code == 404
    assert other.delete(f"/components/{component_id}").status_code == 404
    assert create(other, project_id, plan_id).status_code == 404


def test_deleting_a_plan_or_project_deletes_its_components(client, project_id, plan_id):
    first = create(client, project_id, plan_id).json()["id"]

    assert client.delete(f"/plans/{plan_id}").status_code == 204
    assert client.get(f"/components/{first}").status_code == 404

    other_plan = client.post(f"/projects/{project_id}/plans", json={"title": "Upper"}).json()["id"]
    second = create(client, project_id, other_plan).json()["id"]

    assert client.delete(f"/projects/{project_id}").status_code == 204
    assert client.get(f"/components/{second}").status_code == 404
