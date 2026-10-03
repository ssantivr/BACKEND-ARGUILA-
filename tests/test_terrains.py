import pytest

from tests.helpers import register

TERRAIN = {"name": "Main Lot", "area_m2": 450.5, "slope_percent": 8.5}


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post(
        "/projects", json={"name": "Demo House"}
    )
    return project.json()["id"]


def create_terrain(client, project_id, **overrides):
    return client.post(f"/projects/{project_id}/terrains", json={**TERRAIN, **overrides})


def test_create_and_list_terrains(client, project_id):
    response = create_terrain(client, project_id)

    assert response.status_code == 201
    terrain = response.json()
    assert terrain["project_id"] == project_id
    assert terrain["area_m2"] == 450.5
    assert terrain["slope_percent"] == 8.5
    assert terrain["latitude"] is None

    assert client.get(f"/terrains/{terrain['id']}").json() == terrain
    assert client.get(f"/projects/{project_id}/terrains").json() == [terrain]


def test_terrain_requires_existing_project(client):
    register(client)

    assert create_terrain(client, 999).status_code == 404
    assert client.get("/projects/999/terrains").status_code == 404


@pytest.mark.parametrize(
    "invalid",
    [{"area_m2": 0}, {"area_m2": -5}, {"latitude": 91}, {"longitude": -181}, {"name": ""}],
)
def test_invalid_terrain_is_rejected(client, project_id, invalid):
    assert create_terrain(client, project_id, **invalid).status_code == 422


def test_update_terrain(client, project_id):
    terrain_id = create_terrain(client, project_id).json()["id"]

    response = client.patch(
        f"/terrains/{terrain_id}", json={"soil_type": "clay", "slope_percent": None}
    )

    assert response.status_code == 200
    assert response.json()["soil_type"] == "clay"
    assert response.json()["slope_percent"] is None
    assert response.json()["area_m2"] == 450.5

    assert client.patch(f"/terrains/{terrain_id}", json={"area_m2": 0}).status_code == 422


def test_delete_terrain(client, project_id):
    terrain_id = create_terrain(client, project_id).json()["id"]

    assert client.delete(f"/terrains/{terrain_id}").status_code == 204
    assert client.get(f"/terrains/{terrain_id}").status_code == 404


def test_deleting_project_removes_its_terrains(client, project_id):
    terrain_id = create_terrain(client, project_id).json()["id"]

    client.delete(f"/projects/{project_id}")

    assert client.get(f"/terrains/{terrain_id}").status_code == 404


def test_terrain_dimensions_are_optional_and_validated(client, project_id):
    without = create_terrain(client, project_id).json()
    assert without["width_m"] is None
    assert without["length_m"] is None

    response = create_terrain(client, project_id, name="Back Lot", width_m=15, length_m=30.5)
    assert response.status_code == 201
    assert response.json()["width_m"] == 15
    assert response.json()["length_m"] == 30.5

    updated = client.patch(f"/terrains/{without['id']}", json={"width_m": 12})
    assert updated.json()["width_m"] == 12
    assert updated.json()["length_m"] is None

    assert create_terrain(client, project_id, name="x", width_m=0).status_code == 422
    assert create_terrain(client, project_id, name="x", length_m=-3).status_code == 422
