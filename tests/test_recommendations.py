import pytest

from tests.helpers import register


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post(
        "/projects", json={"name": "Demo House"}
    )
    return project.json()["id"]


def add_terrain(client, project_id, **fields):
    payload = {"name": "Main Lot", "area_m2": 450, **fields}
    return client.post(f"/projects/{project_id}/terrains", json=payload)


def add_material(client, project_id, **fields):
    payload = {"name": "Concrete", "unit": "m3", "quantity": 85, "unit_cost": 110, **fields}
    return client.post(f"/projects/{project_id}/materials", json=payload)


def generate(client, project_id):
    response = client.post(f"/projects/{project_id}/recommendations/generate")
    assert response.status_code == 200
    return response.json()


def contents(recommendations):
    return " | ".join(r["content"] for r in recommendations)


def test_manual_recommendation_crud(client, project_id):
    response = client.post(
        f"/projects/{project_id}/recommendations",
        json={"category": "design", "content": "Orient the living room north."},
    )

    assert response.status_code == 201
    recommendation = response.json()
    assert recommendation["source"] == "user"
    assert recommendation["project_id"] == project_id

    listing = client.get(f"/projects/{project_id}/recommendations")
    assert listing.json() == [recommendation]

    assert client.delete(f"/recommendations/{recommendation['id']}").status_code == 204
    assert client.delete(f"/recommendations/{recommendation['id']}").status_code == 404
    assert client.get(f"/projects/{project_id}/recommendations").json() == []


def test_empty_content_is_rejected(client, project_id):
    response = client.post(
        f"/projects/{project_id}/recommendations",
        json={"category": "design", "content": ""},
    )

    assert response.status_code == 422


def test_requires_existing_project(client):
    register(client)

    payload = {"category": "design", "content": "x"}

    assert client.post("/projects/999/recommendations", json=payload).status_code == 404
    assert client.get("/projects/999/recommendations").status_code == 404
    assert client.post("/projects/999/recommendations/generate").status_code == 404


def test_generate_for_empty_project_asks_for_data(client, project_id):
    generated = generate(client, project_id)

    assert [r["category"] for r in generated] == ["terrain", "materials"]
    assert all(r["source"] == "system" for r in generated)


def test_generate_flags_steep_slope_and_clay_soil(client, project_id):
    add_terrain(client, project_id, slope_percent=22.5, soil_type="Clay")
    add_material(client, project_id)

    generated = generate(client, project_id)

    assert len(generated) == 2
    assert "22.5 %" in contents(generated)
    assert "arcilloso" in contents(generated)


def test_generate_is_silent_for_a_complete_gentle_project(client, project_id):
    add_terrain(client, project_id, slope_percent=3, soil_type="sand")
    add_material(client, project_id)

    assert generate(client, project_id) == []


def test_generate_flags_incomplete_terrain_and_materials(client, project_id):
    add_terrain(client, project_id)
    add_material(client, project_id, name="Brick", unit_cost=0)
    add_material(client, project_id, name="Sand", quantity=0)

    text = contents(generate(client, project_id))

    assert "Completa la pendiente" in text
    assert "no tienen costo unitario" in text and "Brick" in text
    assert "cantidad cero" in text and "Sand" in text


def test_generate_replaces_system_recommendations_but_keeps_user_ones(client, project_id):
    client.post(
        f"/projects/{project_id}/recommendations",
        json={"category": "design", "content": "Keep the oak tree."},
    )

    first = generate(client, project_id)
    second = generate(client, project_id)

    assert [r["content"] for r in first] == [r["content"] for r in second]

    def listed(**params):
        response = client.get(f"/projects/{project_id}/recommendations", params=params)
        return response.json()

    assert len(listed(source="system")) == len(first)
    assert [r["content"] for r in listed(source="user")] == ["Keep the oak tree."]
    assert len(listed()) == len(first) + 1
    assert len(listed(category="terrain")) == 1

    add_terrain(client, project_id, slope_percent=3, soil_type="sand")
    add_material(client, project_id)

    assert generate(client, project_id) == []
    assert [r["source"] for r in listed()] == ["user"]


def test_invalid_source_filter_is_rejected(client, project_id):
    response = client.get(
        f"/projects/{project_id}/recommendations", params={"source": "robot"}
    )

    assert response.status_code == 422
