import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.project_templates import TEMPLATES
from tests.helpers import register


def test_templates_require_authentication(client):
    assert client.get("/templates").status_code == 401
    assert client.post("/templates/vivienda-compacta/projects").status_code == 401


def test_list_templates(client):
    register(client)

    templates = client.get("/templates").json()

    assert [template["id"] for template in templates] == [
        "casa-familiar-andina",
        "vivienda-compacta",
        "edificio-multifamiliar",
        "oficina-profesional",
    ]
    assert templates[0] == {
        "id": "casa-familiar-andina",
        "name": "Casa Familiar Andina",
        "kind": "Casa",
        "description": "Vivienda unifamiliar de dos niveles con estudio, lavandería y jardín posterior.",
        "levels": 2,
        "lot_area_m2": 384,
        "built_area_m2": 203,
    }
    assert [template["built_area_m2"] for template in templates] == [203, 96, 540, 260]


def test_unknown_template_is_not_found(client):
    register(client)

    assert client.post("/templates/castle/projects").status_code == 404


def test_create_project_from_template(client):
    register(client)

    response = client.post("/templates/casa-familiar-andina/projects")

    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "Casa Familiar Andina"
    assert project["status"] == "draft"

    project_id = project["id"]
    terrains = client.get(f"/projects/{project_id}/terrains").json()
    plans = client.get(f"/projects/{project_id}/plans").json()
    rooms = client.get(f"/projects/{project_id}/rooms").json()
    columns = client.get(f"/projects/{project_id}/components").json()

    assert [(terrain["width_m"], terrain["length_m"]) for terrain in terrains] == [(16, 24)]
    assert [(plan["title"], plan["level"]) for plan in plans] == [
        ("Planta baja", "0"),
        ("Planta alta", "1"),
    ]
    assert len(rooms) == 15
    assert sum(room["width_m"] * room["depth_m"] for room in rooms) == pytest.approx(203)
    assert {room["plan_id"] for room in rooms} == {plan["id"] for plan in plans}
    assert [column["kind"] for column in columns] == ["column"] * 8

    structure = client.get(f"/projects/{project_id}/structure").json()

    assert {room["kind"] for room in structure["rooms"]} == {"room"}
    assert sorted({room["base_m"] for room in structure["rooms"]}) == [0, 2.8]


def test_template_with_materials_creates_them_with_the_project(client):
    register(client)

    project = client.post("/templates/vivienda-compacta/projects").json()
    materials = client.get(f"/projects/{project['id']}/materials").json()

    assert project["location"] == "Ibarra, Imbabura"
    assert len(materials) == 8
    assert {material["category"] for material in materials} == {
        "Estructura",
        "Mampostería",
        "Acabados",
        "Carpintería",
        "Cubierta",
    }
    assert all(material["unit_cost"] > 0 for material in materials)


def test_template_without_materials_creates_none(client):
    register(client)

    project = client.post("/templates/oficina-profesional/projects").json()

    assert client.get(f"/projects/{project['id']}/materials").json() == []


def test_creating_the_same_template_twice_picks_a_free_name(client):
    register(client)

    first = client.post("/templates/vivienda-compacta/projects").json()
    second = client.post("/templates/vivienda-compacta/projects").json()
    third = client.post("/templates/vivienda-compacta/projects").json()

    assert [first["name"], second["name"], third["name"]] == [
        "Vivienda compacta",
        "Vivienda compacta (2)",
        "Vivienda compacta (3)",
    ]


def test_template_projects_belong_to_the_user_who_created_them(client):
    register(client)
    project_id = client.post("/templates/oficina-profesional/projects").json()["id"]

    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    assert other.get(f"/projects/{project_id}").status_code == 404
    assert other.get("/projects").json() == []


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda template: template.id)
def test_template_rooms_fit_inside_the_lot_without_overlapping(template):
    for level in template.levels:
        for room in level.rooms:
            assert room.x_m >= 0 and room.y_m >= 0
            assert room.x_m + room.width_m <= template.lot_width_m
            assert room.y_m + room.depth_m <= template.lot_length_m

        for index, first in enumerate(level.rooms):
            for second in level.rooms[index + 1 :]:
                apart = (
                    first.x_m + first.width_m <= second.x_m + 1e-9
                    or second.x_m + second.width_m <= first.x_m + 1e-9
                    or first.y_m + first.depth_m <= second.y_m + 1e-9
                    or second.y_m + second.depth_m <= first.y_m + 1e-9
                )
                assert apart, (level.title, first.name, second.name)
