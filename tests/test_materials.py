import pytest

CONCRETE = {
    "name": "Concrete",
    "category": "structure",
    "unit": "m3",
    "quantity": 85,
    "unit_cost": 110.25,
}
BRICK = {"name": "Brick", "category": "masonry", "unit": "unit"}


@pytest.fixture
def project_id(client):
    owner = client.post("/users", json={"name": "Ana", "email": "ana@example.com"})
    project = client.post(
        "/projects", json={"owner_id": owner.json()["id"], "name": "Demo House"}
    )
    return project.json()["id"]


def create_material(client, project_id, payload=CONCRETE, **overrides):
    return client.post(
        f"/projects/{project_id}/materials", json={**payload, **overrides}
    )


def test_create_and_get_material(client, project_id):
    response = create_material(client, project_id)

    assert response.status_code == 201
    material = response.json()
    assert material["project_id"] == project_id
    assert material["quantity"] == 85
    assert material["unit_cost"] == 110.25

    assert client.get(f"/materials/{material['id']}").json() == material


def test_quantity_and_cost_default_to_zero(client, project_id):
    response = create_material(client, project_id, BRICK)

    assert response.status_code == 201
    assert response.json()["quantity"] == 0
    assert response.json()["unit_cost"] == 0


def test_material_requires_existing_project(client):
    assert create_material(client, 999).status_code == 404
    assert client.get("/projects/999/materials").status_code == 404


def test_duplicate_material_name_in_project_is_rejected(client, project_id):
    create_material(client, project_id)

    assert create_material(client, project_id).status_code == 409


@pytest.mark.parametrize("invalid", [{"quantity": -1}, {"unit_cost": -0.5}, {"unit": ""}])
def test_invalid_material_is_rejected(client, project_id, invalid):
    assert create_material(client, project_id, **invalid).status_code == 422


def test_list_filters_by_category(client, project_id):
    create_material(client, project_id)
    create_material(client, project_id, BRICK)

    def names(**params):
        response = client.get(f"/projects/{project_id}/materials", params=params)
        return [m["name"] for m in response.json()]

    assert names() == ["Concrete", "Brick"]
    assert names(category="masonry") == ["Brick"]
    assert names(category="finishes") == []


def test_update_material(client, project_id):
    material_id = create_material(client, project_id).json()["id"]
    create_material(client, project_id, BRICK)

    response = client.patch(f"/materials/{material_id}", json={"quantity": 90.5})

    assert response.status_code == 200
    assert response.json()["quantity"] == 90.5
    assert response.json()["unit_cost"] == 110.25

    conflict = client.patch(f"/materials/{material_id}", json={"name": "Brick"})
    assert conflict.status_code == 409


def test_delete_material(client, project_id):
    material_id = create_material(client, project_id).json()["id"]

    assert client.delete(f"/materials/{material_id}").status_code == 204
    assert client.get(f"/materials/{material_id}").status_code == 404
