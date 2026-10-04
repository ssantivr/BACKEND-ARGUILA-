import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import register

ORIGIN = "http://localhost:5173"


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


def structure(client, project_id):
    return client.get(f"/projects/{project_id}/structure")


def test_structure_requires_authentication(client):
    assert client.get("/projects/1/structure").status_code == 401


def test_structure_is_hidden_from_other_users(client, project_id):
    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    assert structure(other, project_id).status_code == 404
    assert structure(client, 9999).status_code == 404


def test_structure_is_empty_without_terrains(client, project_id):
    client.post(f"/projects/{project_id}/plans", json={"title": "Ground floor"})

    assert structure(client, project_id).json() == {
        "project_id": project_id,
        "roof": "gable",
        "terrains": [],
        "rooms": [],
        "components": [],
    }


def test_structure_stacks_one_storey_per_plan_inside_the_setback(client, project_id):
    terrain = client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 600, "width_m": 20, "length_m": 30},
    ).json()
    ground = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "level": "0"}
    ).json()
    upper = client.post(
        f"/projects/{project_id}/plans", json={"title": "Upper floor", "level": "1"}
    ).json()

    body = structure(client, project_id).json()

    assert body["terrains"] == [
        {
            "id": terrain["id"],
            "name": "Lot",
            "outline": [
                {"x_m": 0, "y_m": 0},
                {"x_m": 20, "y_m": 0},
                {"x_m": 20, "y_m": 30},
                {"x_m": 0, "y_m": 30},
            ],
        }
    ]
    assert body["rooms"] == [
        {
            "kind": "volume",
            "id": ground["id"],
            "plan_id": ground["id"],
            "plan_title": "Ground floor",
            "name": "Ground floor",
            "level": "0",
            "x_m": 10,
            "y_m": 15,
            "base_m": 0,
            "width_m": 14,
            "depth_m": 24,
            "height_m": 3,
            "surface": None,
        },
        {
            "kind": "volume",
            "id": upper["id"],
            "plan_id": upper["id"],
            "plan_title": "Upper floor",
            "name": "Upper floor",
            "level": "1",
            "x_m": 10,
            "y_m": 15,
            "base_m": 3,
            "width_m": 14,
            "depth_m": 24,
            "height_m": 3,
            "surface": None,
        },
    ]


def test_structure_shrinks_the_setback_on_a_narrow_lot(client, project_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Narrow", "area_m2": 80, "width_m": 4, "length_m": 20},
    )
    client.post(f"/projects/{project_id}/plans", json={"title": "Ground floor", "level": "0"})

    room = structure(client, project_id).json()["rooms"][0]

    assert (room["width_m"], room["depth_m"]) == (2, 18)


def test_structure_places_terrains_side_by_side_and_builds_on_the_rectangular_one(
    client, project_id
):
    triangle = [{"x_m": 5, "y_m": 5}, {"x_m": 15, "y_m": 5}, {"x_m": 5, "y_m": 25}]
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Triangle", "area_m2": 100, "points": triangle},
    )
    client.post(f"/projects/{project_id}/terrains", json={"name": "No size", "area_m2": 50})
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 400, "width_m": 20, "length_m": 20},
    )
    client.post(f"/projects/{project_id}/plans", json={"title": "Ground floor", "level": "0"})

    body = structure(client, project_id).json()

    assert [terrain["name"] for terrain in body["terrains"]] == ["Triangle", "Lot"]
    assert body["terrains"][0]["outline"] == [
        {"x_m": 0, "y_m": 0},
        {"x_m": 10, "y_m": 0},
        {"x_m": 0, "y_m": 20},
    ]
    assert body["terrains"][1]["outline"][0] == {"x_m": 15, "y_m": 0}
    assert body["rooms"][0]["x_m"] == 25


def test_structure_draws_rooms_and_no_volumes_once_a_plan_has_rooms(client, project_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 600, "width_m": 20, "length_m": 30},
    )
    ground = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()
    upper = client.post(
        f"/projects/{project_id}/plans", json={"title": "Upper", "level": "1"}
    ).json()
    room = {"plan_id": ground["id"], "x_m": 3, "y_m": 4, "width_m": 5, "depth_m": 6}
    kitchen = client.post(
        f"/projects/{project_id}/rooms", json={**room, "name": "Kitchen", "height_m": 4}
    ).json()
    client.post(f"/projects/{project_id}/rooms", json={**room, "name": "Hall", "x_m": 8})

    rooms = structure(client, project_id).json()["rooms"]

    client.post(
        f"/projects/{project_id}/rooms",
        json={**room, "plan_id": upper["id"], "name": "Bedroom"},
    )
    client.post(f"/projects/{project_id}/plans", json={"title": "Attic", "level": "2"})

    rooms = structure(client, project_id).json()["rooms"]

    assert [(item["kind"], item["name"], item["base_m"]) for item in rooms] == [
        ("room", "Kitchen", 0),
        ("room", "Hall", 0),
        ("room", "Bedroom", 4),
    ]
    assert rooms[0] == {
        "kind": "room",
        "id": kitchen["id"],
        "plan_id": ground["id"],
        "plan_title": "Ground",
        "name": "Kitchen",
        "level": None,
        "x_m": 5.5,
        "y_m": 7,
        "base_m": 0,
        "width_m": 5,
        "depth_m": 6,
        "height_m": 4,
        "surface": None,
    }
    assert rooms[2]["plan_id"] == upper["id"]


def test_structure_keeps_the_height_of_an_empty_level_between_rooms(client, project_id):
    ground = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()
    client.post(f"/projects/{project_id}/plans", json={"title": "Middle", "level": "1"})
    upper = client.post(f"/projects/{project_id}/plans", json={"title": "Upper"}).json()
    room = {"name": "Hall", "x_m": 0, "y_m": 0, "width_m": 4, "depth_m": 4}
    client.post(f"/projects/{project_id}/rooms", json={**room, "plan_id": ground["id"]})
    client.post(f"/projects/{project_id}/rooms", json={**room, "plan_id": upper["id"]})

    rooms = structure(client, project_id).json()["rooms"]

    assert [(item["plan_title"], item["base_m"]) for item in rooms] == [
        ("Ground", 0),
        ("Upper", 6),
    ]


def test_structure_skips_plans_that_are_not_a_floor(client, project_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 600, "width_m": 20, "length_m": 30},
    )
    for title, level in [
        ("Ground", "0"),
        ("Site plan", "Terreno"),
        ("Details", None),
        ("Mezzanine", "0.5"),
        ("Basement", "-1"),
    ]:
        client.post(f"/projects/{project_id}/plans", json={"title": title, "level": level})

    rooms = structure(client, project_id).json()["rooms"]

    assert [(room["name"], room["base_m"]) for room in rooms] == [
        ("Ground", 0),
        ("Mezzanine", 3),
        ("Basement", 6),
    ]


def test_structure_places_components_on_their_level(client, project_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 600, "width_m": 20, "length_m": 30},
    )
    ground = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()
    client.post(f"/projects/{project_id}/plans", json={"title": "Upper", "level": "1"})
    base = {"plan_id": ground["id"], "x_m": 2, "y_m": 4}
    column = client.post(
        f"/projects/{project_id}/components",
        json={**base, "kind": "column", "name": "C1", "width_m": 0.4, "depth_m": 0.4, "height_m": 3.5},
    ).json()
    client.post(
        f"/projects/{project_id}/components",
        json={**base, "kind": "beam", "name": "V1", "width_m": 6, "depth_m": 0.3, "height_m": 0.5},
    )

    body = structure(client, project_id).json()

    assert body["components"][0] == {
        "kind": "column",
        "id": column["id"],
        "plan_id": ground["id"],
        "plan_title": "Ground",
        "name": "C1",
        "level": None,
        "x_m": 2.2,
        "y_m": 4.2,
        "base_m": 0,
        "width_m": 0.4,
        "depth_m": 0.4,
        "height_m": 3.5,
        "surface": None,
    }
    assert [(item["name"], item["base_m"]) for item in body["components"]] == [
        ("C1", 0),
        ("V1", 3),
    ]
    assert body["rooms"] == []


def test_structure_hangs_a_lone_beam_from_the_default_storey_height(client, project_id):
    plan = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()
    client.post(
        f"/projects/{project_id}/components",
        json={
            "plan_id": plan["id"],
            "kind": "beam",
            "name": "V1",
            "x_m": 0,
            "y_m": 0,
            "width_m": 5,
            "depth_m": 0.3,
            "height_m": 0.4,
            "surface": None,
        },
    )

    component = structure(client, project_id).json()["components"][0]

    assert component["base_m"] == 2.6


def test_structure_shows_rooms_without_any_terrain(client, project_id):
    plan = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()
    client.post(
        f"/projects/{project_id}/rooms",
        json={"plan_id": plan["id"], "name": "Hall", "x_m": 0, "y_m": 0, "width_m": 4, "depth_m": 4},
    )

    body = structure(client, project_id).json()

    assert body["terrains"] == []
    assert [room["name"] for room in body["rooms"]] == ["Hall"]


def test_cors_allows_the_application_origin_with_credentials(client):
    response = client.get("/health", headers={"Origin": ORIGIN})

    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_answers_the_preflight_request(client):
    response = client.options(
        "/projects/1/structure",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_cors_ignores_unknown_origins(client):
    response = client.get("/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def surface_url(project_id, kind, element_id):
    return f"/projects/{project_id}/structure/{kind}/{element_id}/surface"


@pytest.fixture
def modelled(client, project_id):
    plan = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "level": "0"}
    ).json()
    base = {"plan_id": plan["id"], "x_m": 0, "y_m": 0, "width_m": 4, "depth_m": 3, "height_m": 3}
    room = client.post(f"/projects/{project_id}/rooms", json={**base, "name": "Hall"}).json()
    column = client.post(
        f"/projects/{project_id}/components", json={**base, "kind": "column", "name": "C1"}
    ).json()

    return {"plan": plan["id"], "room": room["id"], "column": column["id"]}


def test_surface_of_a_room_and_a_component_is_saved(client, project_id, modelled):
    room = client.patch(surface_url(project_id, "room", modelled["room"]), json={"surface": "glass"})
    column = client.patch(
        surface_url(project_id, "column", modelled["column"]), json={"surface": "steel"}
    )

    body = structure(client, project_id).json()

    assert (room.status_code, column.status_code) == (204, 204)
    assert body["rooms"][0]["surface"] == "glass"
    assert body["components"][0]["surface"] == "steel"


def test_surface_of_a_volume_is_saved_on_its_plan(client, project_id):
    client.post(
        f"/projects/{project_id}/terrains",
        json={"name": "Lot", "area_m2": 600, "width_m": 20, "length_m": 30},
    )
    plan = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "level": "0"}
    ).json()

    response = client.patch(surface_url(project_id, "volume", plan["id"]), json={"surface": "wood"})

    assert response.status_code == 204
    assert structure(client, project_id).json()["rooms"][0]["surface"] == "wood"


def test_surface_rejects_an_unknown_material_or_kind(client, project_id, modelled):
    url = surface_url(project_id, "room", modelled["room"])

    assert client.patch(url, json={"surface": "gold"}).status_code == 422
    assert (
        client.patch(surface_url(project_id, "roof", 1), json={"surface": "glass"}).status_code
        == 422
    )


def test_surface_needs_an_element_of_that_kind_in_the_project(client, project_id, modelled):
    other_project = client.post("/projects", json={"name": "Other"}).json()["id"]
    body = {"surface": "glass"}

    assert client.patch(surface_url(project_id, "room", 9999), json=body).status_code == 404
    assert (
        client.patch(surface_url(project_id, "beam", modelled["column"]), json=body).status_code
        == 404
    )
    assert (
        client.patch(surface_url(other_project, "room", modelled["room"]), json=body).status_code
        == 404
    )


def test_surface_is_hidden_from_other_users(client, project_id, modelled):
    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")
    url = surface_url(project_id, "room", modelled["room"])

    assert other.patch(url, json={"surface": "glass"}).status_code == 404
    assert TestClient(app).patch(url, json={"surface": "glass"}).status_code == 401


def test_roof_is_gable_until_it_is_changed(client, project_id):
    url = f"/projects/{project_id}/structure/roof"

    assert structure(client, project_id).json()["roof"] == "gable"
    assert client.patch(url, json={"roof": "flat"}).status_code == 204
    assert structure(client, project_id).json()["roof"] == "flat"


def test_roof_rejects_an_unknown_kind(client, project_id):
    response = client.patch(f"/projects/{project_id}/structure/roof", json={"roof": "dome"})

    assert response.status_code == 422


def test_roof_is_hidden_from_other_users(client, project_id):
    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")
    url = f"/projects/{project_id}/structure/roof"

    assert other.patch(url, json={"roof": "flat"}).status_code == 404
    assert TestClient(app).patch(url, json={"roof": "flat"}).status_code == 401
    assert structure(client, project_id).json()["roof"] == "gable"
