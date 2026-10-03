import pytest


@pytest.fixture
def owner_id(client):
    response = client.post("/users", json={"name": "Ana", "email": "ana@example.com"})
    return response.json()["id"]


def create_project(client, owner_id, name="Demo House", **extra):
    return client.post("/projects", json={"owner_id": owner_id, "name": name, **extra})


def test_create_project(client, owner_id):
    response = create_project(client, owner_id, location="Quito")

    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "Demo House"
    assert project["status"] == "draft"
    assert project["location"] == "Quito"
    assert client.get(f"/projects/{project['id']}").json() == project


def test_create_project_requires_existing_owner(client):
    assert create_project(client, owner_id=999).status_code == 404


def test_duplicate_name_for_same_owner_is_rejected(client, owner_id):
    create_project(client, owner_id)

    assert create_project(client, owner_id).status_code == 409


def test_invalid_status_is_rejected(client, owner_id):
    assert create_project(client, owner_id, status="finished").status_code == 422


def test_list_filters_by_search_status_and_owner(client, owner_id):
    create_project(client, owner_id, name="Lake House", status="active")
    create_project(client, owner_id, name="City Tower")

    def names(**params):
        return [p["name"] for p in client.get("/projects", params=params).json()]

    assert names() == ["Lake House", "City Tower"]
    assert names(search="house") == ["Lake House"]
    assert names(status="draft") == ["City Tower"]
    assert names(owner_id=owner_id + 1) == []
    assert names(search="%") == []


def test_update_project(client, owner_id):
    project_id = create_project(client, owner_id).json()["id"]
    create_project(client, owner_id, name="City Tower")

    response = client.patch(f"/projects/{project_id}", json={"status": "active"})

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["name"] == "Demo House"

    conflict = client.patch(f"/projects/{project_id}", json={"name": "City Tower"})
    assert conflict.status_code == 409


def test_delete_project(client, owner_id):
    project_id = create_project(client, owner_id).json()["id"]

    assert client.delete(f"/projects/{project_id}").status_code == 204
    assert client.get(f"/projects/{project_id}").status_code == 404
    assert client.delete(f"/projects/{project_id}").status_code == 404
