import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.models import Role, User
from tests.helpers import PASSWORD, ROLE_PERMISSIONS, register, set_roles

API = "/api/v1"
SECRET = "a-test-secret-that-is-long-enough-to-sign"
ELEMENT = {
    "layer": "installations",
    "kind": "water_pipe",
    "name": "Cold water pipe",
    "min_x_m": 1,
    "min_y_m": 2,
    "min_z_m": 0.3,
    "max_x_m": 4,
    "max_y_m": 2.1,
    "max_z_m": 0.4,
}


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


@pytest.fixture
def room_id(client, project_id):
    plan_id = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()["id"]
    room = {"plan_id": plan_id, "name": "Kitchen", "x_m": 0, "y_m": 0, "width_m": 5, "depth_m": 4}

    return client.post(f"/projects/{project_id}/rooms", json=room).json()["id"]


@pytest.fixture
def unit_id(client, project_id):
    property_id = client.post(
        f"{API}/properties", json={"project_id": project_id, "name": "House"}
    ).json()["id"]

    return client.post(
        f"{API}/units", json={"property_id": property_id, "code": "A-1", "name": "Unit A"}
    ).json()["id"]


@pytest.fixture
def stranger(client, project_id):
    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    return other


def test_the_api_answers_unauthenticated_calls_in_spanish(client):
    response = client.get(f"{API}/units")

    assert response.status_code == 401
    assert response.json()["detail"] == "Tu sesión terminó. Vuelve a iniciar sesión."


def test_a_new_user_is_an_architect(client, project_id):
    access = client.get(f"{API}/auth/me").json()

    assert access["roles"] == ["architect"]
    assert access["permissions"] == sorted(ROLE_PERMISSIONS["architect"])


def test_the_stored_roles_match_the_documented_catalog(client, engine):
    with Session(engine) as session:
        stored = {
            role.name: {permission.code for permission in role.permissions}
            for role in session.scalars(select(Role))
        }

    assert stored == ROLE_PERMISSIONS


def test_properties_and_units_are_created_listed_and_edited(client, project_id):
    created = client.post(
        f"{API}/properties",
        json={"project_id": project_id, "name": "House", "spatial_metadata": {"up_axis": "z"}},
    )

    assert created.status_code == 201
    property_id = created.json()["id"]
    assert created.json()["spatial_metadata"] == {"up_axis": "z"}
    assert created.json()["status"] == "planning"

    unit = client.post(
        f"{API}/units",
        json={
            "property_id": property_id,
            "code": "A-1",
            "name": "Unit A",
            "price": 120000.5,
            "asset_config": {"lod": 2},
        },
    )

    assert unit.status_code == 201
    assert (unit.json()["price"], unit.json()["currency"]) == (120000.5, "USD")
    assert unit.json()["asset_config"] == {"lod": 2}

    unit_id = unit.json()["id"]
    edited = client.patch(f"{API}/units/{unit_id}", json={"status": "sold", "price": None})

    assert edited.status_code == 200
    assert (edited.json()["status"], edited.json()["price"]) == ("sold", None)
    assert [item["id"] for item in client.get(f"{API}/units?status=sold").json()] == [unit_id]
    assert client.get(f"{API}/units?status=available").json() == []
    assert len(client.get(f"{API}/properties?project_id={project_id}").json()) == 1


def test_duplicates_are_refused_with_a_spanish_message(client, project_id, unit_id):
    property_id = client.get(f"{API}/units/{unit_id}").json()["property_id"]

    duplicate = client.post(
        f"{API}/units", json={"property_id": property_id, "code": "A-1", "name": "Again"}
    )
    same_name = client.post(f"{API}/properties", json={"project_id": project_id, "name": "House"})

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "La propiedad ya tiene una unidad con ese código."
    assert same_name.status_code == 409


def test_validation_errors_are_in_spanish_only_under_the_api_prefix(client, project_id):
    response = client.post(f"{API}/units", json={"name": "", "price": -1, "status": "gone"})
    messages = {issue["loc"][-1]: issue["msg"] for issue in response.json()["detail"]}

    assert response.status_code == 422
    assert messages["property_id"] == "Este campo es obligatorio."
    assert messages["name"] == "No puede estar vacío."
    assert messages["price"] == "Debe ser mayor o igual que 0."
    assert messages["status"].startswith("Valor no permitido. Opciones:")

    legacy = client.post("/projects", json={})

    assert legacy.json()["detail"][0]["msg"] == "Field required"


def test_other_users_cannot_see_or_change_units(client, project_id, unit_id, stranger):
    property_id = client.get(f"{API}/units/{unit_id}").json()["property_id"]

    assert stranger.get(f"{API}/units").json() == []
    assert stranger.get(f"{API}/units/{unit_id}").status_code == 404
    assert stranger.patch(f"{API}/units/{unit_id}", json={"name": "Mine"}).status_code == 404
    assert stranger.delete(f"{API}/units/{unit_id}").status_code == 404
    assert stranger.get(f"{API}/properties/{property_id}").status_code == 404
    assert (
        stranger.post(
            f"{API}/units", json={"property_id": property_id, "code": "B", "name": "B"}
        ).status_code
        == 404
    )
    assert (
        stranger.post(f"{API}/properties", json={"project_id": project_id, "name": "Other"}).json()[
            "detail"
        ]
        == "Proyecto no encontrado."
    )


def test_a_viewer_reads_but_cannot_write(client, engine, project_id, unit_id):
    set_roles(engine, "ana@example.com", "viewer")

    assert client.get(f"{API}/units/{unit_id}").status_code == 200

    refused = client.patch(f"{API}/units/{unit_id}", json={"name": "New"})

    assert refused.status_code == 403
    assert refused.json()["detail"] == "No tienes permiso para realizar esta acción."
    assert client.delete(f"{API}/units/{unit_id}").status_code == 403
    assert client.post(f"{API}/spatial-data/elements", json=ELEMENT).status_code == 403


def test_a_user_without_roles_is_refused(client, engine, project_id):
    set_roles(engine, "ana@example.com")

    assert client.get(f"{API}/units").status_code == 403
    assert client.get(f"{API}/auth/me").json()["permissions"] == []


def test_only_an_admin_assigns_roles(client, engine, project_id, stranger):
    with Session(engine) as session:
        eve_id = session.scalar(select(User.id).where(User.email == "eve@example.com"))

    assert (
        client.patch(f"{API}/users/{eve_id}/roles", json={"roles": ["viewer"]}).status_code == 403
    )

    set_roles(engine, "ana@example.com", "admin")
    assigned = client.patch(f"{API}/users/{eve_id}/roles", json={"roles": ["viewer"]})

    assert assigned.status_code == 200
    assert assigned.json()["roles"] == ["viewer"]
    assert (
        stranger.post(f"{API}/properties", json={"project_id": 1, "name": "X"}).status_code == 403
    )
    assert client.patch(f"{API}/users/{eve_id}/roles", json={"roles": ["owner"]}).status_code == 422
    assert client.patch(f"{API}/users/9999/roles", json={"roles": ["viewer"]}).status_code == 404


def test_access_tokens_need_a_configured_secret(client, project_id, monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    credentials = {"email": "ana@example.com", "password": PASSWORD}

    assert client.post(f"{API}/auth/token", json=credentials).status_code == 503

    monkeypatch.setenv("JWT_SECRET", "too-short")

    assert client.post(f"{API}/auth/token", json=credentials).status_code == 503


def test_a_bearer_token_opens_the_api_without_a_cookie(client, engine, project_id, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET)
    credentials = {"email": "ana@example.com", "password": PASSWORD}

    assert (
        client.post(f"{API}/auth/token", json={**credentials, "password": "wrong"}).status_code
        == 401
    )

    issued = client.post(f"{API}/auth/token", json=credentials).json()
    headers = {"Authorization": f"Bearer {issued['access_token']}"}
    anonymous = TestClient(app)

    assert issued["token_type"] == "bearer"
    assert issued["expires_in"] == 900
    assert anonymous.get(f"{API}/auth/me", headers=headers).json()["email"] == "ana@example.com"
    assert anonymous.get(f"{API}/units", headers=headers).status_code == 200
    assert (
        anonymous.get(f"{API}/units", headers={"Authorization": "Bearer nope"}).status_code == 401
    )
    assert anonymous.get(f"{API}/units", headers={"Authorization": "Basic abc"}).status_code == 401
    assert anonymous.get(f"/projects/{project_id}", headers=headers).status_code == 401

    monkeypatch.setenv("JWT_SECRET", SECRET + "-rotated")

    assert anonymous.get(f"{API}/units", headers=headers).status_code == 401

    monkeypatch.setenv("JWT_SECRET", SECRET)

    with Session(engine) as session:
        session.scalar(select(User)).password_hash = "changed"
        session.commit()

    assert anonymous.get(f"{API}/units", headers=headers).status_code == 401


def test_room_spatial_metadata(client, project_id, room_id, unit_id):
    listed = client.get(f"{API}/rooms?project_id={project_id}").json()

    assert [(room["id"], room["category"], room["unit_id"]) for room in listed] == [
        (room_id, "other", None)
    ]

    edited = client.patch(
        f"{API}/rooms/{room_id}",
        json={"unit_id": unit_id, "category": "kitchen", "mesh_ref": "meshes/kitchen.glb"},
    )

    assert edited.status_code == 200
    assert edited.json()["category"] == "kitchen"
    assert len(client.get(f"{API}/rooms?project_id={project_id}&category=kitchen").json()) == 1
    assert client.get(f"{API}/rooms?project_id={project_id}&category=bedroom").json() == []
    assert len(client.get(f"{API}/rooms?project_id={project_id}&unit_id={unit_id}").json()) == 1

    cleared = client.patch(f"{API}/rooms/{room_id}", json={"unit_id": None})

    assert cleared.json()["unit_id"] is None
    assert cleared.json()["category"] == "kitchen"
    assert client.patch(f"{API}/rooms/{room_id}", json={"category": "attic"}).status_code == 422
    assert client.get(f"/rooms/{room_id}").json()["name"] == "Kitchen"


def test_a_room_only_joins_a_unit_of_its_own_project(client, project_id, room_id):
    other_project = client.post("/projects", json={"name": "Tower"}).json()["id"]
    other_property = client.post(
        f"{API}/properties", json={"project_id": other_project, "name": "Tower"}
    ).json()["id"]
    foreign_unit = client.post(
        f"{API}/units", json={"property_id": other_property, "code": "T-1", "name": "T"}
    ).json()["id"]

    assert client.patch(f"{API}/rooms/{room_id}", json={"unit_id": foreign_unit}).status_code == 404
    assert client.patch(f"{API}/rooms/{room_id}", json={"unit_id": 9999}).status_code == 404


def test_deleting_a_unit_keeps_its_rooms(client, project_id, room_id, unit_id):
    client.patch(f"{API}/rooms/{room_id}", json={"unit_id": unit_id})

    assert client.delete(f"{API}/units/{unit_id}").status_code == 204
    assert client.get(f"{API}/rooms/{room_id}").json()["unit_id"] is None


def test_spatial_elements_are_filtered_by_layer_status_and_footprint(client, project_id, room_id):
    pipe = client.post(
        f"{API}/spatial-data/elements",
        json={**ELEMENT, "project_id": project_id, "room_id": room_id, "config": {"dn": 20}},
    )
    floor = client.post(
        f"{API}/spatial-data/elements",
        json={
            **ELEMENT,
            "project_id": project_id,
            "layer": "finishes",
            "kind": "flooring",
            "name": "Oak floor",
            "work_status": "planned",
            "min_x_m": 10,
            "max_x_m": 14,
            "min_y_m": 10,
            "max_y_m": 13,
        },
    )

    assert pipe.status_code == 201 and floor.status_code == 201
    assert pipe.json()["source"] == "manual"
    assert pipe.json()["config"] == {"dn": 20}

    def names(query=""):
        data = client.get(f"{API}/spatial-data?project_id={project_id}{query}").json()

        return [element["name"] for element in data["elements"]]

    everything = client.get(f"{API}/spatial-data?project_id={project_id}").json()

    assert everything["counts"] == {"structure": 0, "installations": 1, "finishes": 1}
    assert names() == ["Cold water pipe", "Oak floor"]
    assert names("&layer=finishes") == ["Oak floor"]
    assert names("&work_status=planned") == ["Oak floor"]
    assert names(f"&room_id={room_id}") == ["Cold water pipe"]
    assert names("&bbox=0,0,5,5") == ["Cold water pipe"]
    assert names("&bbox=9,9,20,20") == ["Oak floor"]
    assert names("&bbox=4,2.1,10,10") == ["Cold water pipe", "Oak floor"]
    assert names("&bbox=50,50,60,60") == []
    assert client.get(f"{API}/spatial-data?project_id={project_id}&bbox=1,2").status_code == 422
    assert client.get(f"{API}/spatial-data?project_id={project_id}&layer=roof").status_code == 422
    assert client.get(f"{API}/spatial-data").status_code == 422


def test_spatial_element_bounds_must_enclose_a_volume(client, project_id):
    flat = client.post(
        f"{API}/spatial-data/elements", json={**ELEMENT, "project_id": project_id, "max_z_m": 0.3}
    )

    assert flat.status_code == 422
    assert flat.json()["detail"][0]["msg"] == "max_z_m debe ser mayor que min_z_m."

    element_id = client.post(
        f"{API}/spatial-data/elements", json={**ELEMENT, "project_id": project_id}
    ).json()["id"]
    inverted = client.patch(f"{API}/spatial-data/elements/{element_id}", json={"max_x_m": 0})

    assert inverted.status_code == 422
    assert inverted.json()["detail"] == "max_x_m debe ser mayor que min_x_m."
    assert client.get(f"{API}/spatial-data/elements/{element_id}").json()["max_x_m"] == 4

    moved = client.patch(
        f"{API}/spatial-data/elements/{element_id}",
        json={"max_x_m": 6, "work_status": "demolition"},
    )

    assert (moved.json()["max_x_m"], moved.json()["work_status"]) == (6, "demolition")
    assert client.delete(f"{API}/spatial-data/elements/{element_id}").status_code == 204
    assert client.get(f"{API}/spatial-data/elements/{element_id}").status_code == 404


def test_deleting_a_room_keeps_its_elements_and_logs(client, project_id, room_id):
    element_id = client.post(
        f"{API}/spatial-data/elements",
        json={**ELEMENT, "project_id": project_id, "room_id": room_id},
    ).json()["id"]
    log_id = client.post(
        f"{API}/interior-walkthrough/logs",
        json={
            "project_id": project_id,
            "room_id": room_id,
            "spatial_element_id": element_id,
            "layer": "installations",
            "title": "Replace the pipe",
        },
    ).json()["id"]

    assert client.delete(f"/rooms/{room_id}").status_code == 204
    assert client.get(f"{API}/spatial-data/elements/{element_id}").json()["room_id"] is None

    logs = client.get(f"{API}/interior-walkthrough/logs?project_id={project_id}").json()

    assert [(log["id"], log["room_id"], log["spatial_element_id"]) for log in logs] == [
        (log_id, None, element_id)
    ]

    assert client.delete(f"/projects/{project_id}").status_code == 204
    assert client.get(f"{API}/spatial-data/elements/{element_id}").status_code == 404


def test_importing_the_native_format_twice_updates_instead_of_duplicating(client, project_id):
    document = {
        "elements": [
            {
                "id": "duct-1",
                "name": "Supply duct",
                "kind": "hvac_duct",
                "work_status": "planned",
                "bounds": {"min": [0, 0, 2.4], "max": [5, 0.4, 2.7]},
            },
            {"id": "floor", "layer": "finishes", "bounds": {"min": [0, 0, 0], "max": [5, 4, 0]}},
        ]
    }
    body = {"project_id": project_id, "provider": "native", "document": document}

    first = client.post(f"{API}/spatial-data/import", json=body)

    assert first.status_code == 200
    assert (first.json()["created"], first.json()["updated"]) == (2, 0)

    duct, floor = first.json()["elements"]

    assert (duct["layer"], duct["work_status"], duct["source"]) == (
        "installations",
        "planned",
        "native",
    )
    assert (floor["layer"], floor["name"]) == ("finishes", "Elemento 2")
    assert (floor["min_z_m"], floor["max_z_m"]) == (0, 0.01)

    document["elements"][0]["bounds"]["max"] = [6, 0.4, 2.7]
    second = client.post(f"{API}/spatial-data/import", json=body)

    assert (second.json()["created"], second.json()["updated"]) == (0, 2)
    assert second.json()["elements"][0]["max_x_m"] == 6
    assert len(client.get(f"{API}/spatial-data?project_id={project_id}").json()["elements"]) == 2


def test_importing_gltf_places_nodes_in_plan_coordinates(client, project_id):
    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [
            {"name": "Level", "translation": [10, 3, 0], "children": [1, 2]},
            {"name": "Beam", "mesh": 0, "extras": {"layer": "structure", "kind": "beam"}},
            {
                "name": "Turned beam",
                "mesh": 0,
                "rotation": [0, 0.7071068, 0, 0.7071068],
                "scale": [2, 1, 1],
            },
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"min": [0, 0, -0.2], "max": [4, 0.5, 0.2]}],
    }

    response = client.post(
        f"{API}/spatial-data/import",
        json={"project_id": project_id, "provider": "gltf", "document": document},
    )

    assert response.status_code == 200, response.text

    beam, turned = response.json()["elements"]

    assert (beam["layer"], beam["kind"], beam["mesh_ref"]) == ("structure", "beam", "meshes/0")
    assert (beam["min_x_m"], beam["max_x_m"]) == (10, 14)
    assert (beam["min_y_m"], beam["max_y_m"]) == (-0.2, 0.2)
    assert (beam["min_z_m"], beam["max_z_m"]) == (3, 3.5)

    # A quarter turn around the vertical axis lays the 8 m long scaled beam along the plan's y.
    assert turned["layer"] == "installations"
    assert (turned["min_x_m"], turned["max_x_m"]) == (9.8, 10.2)
    assert (turned["min_y_m"], turned["max_y_m"]) == (0, 8)


def test_import_refuses_what_it_cannot_read(client, project_id):
    def send(provider, document):
        return client.post(
            f"{API}/spatial-data/import",
            json={"project_id": project_id, "provider": provider, "document": document},
        )

    assert client.get(f"{API}/spatial-data/providers").json() == ["gltf", "native"]
    assert send("revit", {}).status_code == 404
    assert send("native", {}).json()["detail"] == "El documento debe tener una lista «elements»."
    assert send("native", {"elements": []}).status_code == 422
    assert (
        send("native", {"elements": [{"bounds": {"min": [0, 0], "max": [1, 1, 1]}}]}).status_code
        == 422
    )
    assert send("native", {"elements": ["pipe"]}).status_code == 422
    assert send("gltf", {"asset": {"version": "1.0"}}).status_code == 422
    assert (
        send("gltf", {"asset": {"version": "2.0"}, "nodes": [{"children": [0]}]}).status_code == 422
    )
    assert (
        send(
            "gltf",
            {"asset": {"version": "2.0"}, "nodes": [{"mesh": 0}], "meshes": [7], "accessors": []},
        ).status_code
        == 422
    )
    assert (
        send(
            "native",
            {"elements": [{"bounds": {"min": [0, 0, 0], "max": [900000, 1, 1]}}]},
        ).status_code
        == 422
    )
    assert client.get(f"{API}/spatial-data?project_id={project_id}").json()["elements"] == []


def test_walkthrough_steps_keep_their_order(client, project_id, room_id):
    def add(title, **extra):
        return client.post(
            f"{API}/interior-walkthrough/steps",
            json={"project_id": project_id, "title": title, **extra},
        )

    first = add("Sala / Comedor", room_id=room_id, view_config={"cut_fraction": 0.8})
    second = add("Habitación principal", duration_ms=7000)

    assert first.status_code == 201
    assert (first.json()["position"], second.json()["position"]) == (0, 1)
    assert first.json()["duration_ms"] == 5000
    assert add("Too fast", duration_ms=10).status_code == 422
    assert add("Foreign room", room_id=9999).status_code == 404

    client.patch(f"{API}/interior-walkthrough/steps/{second.json()['id']}", json={"position": 0})
    client.patch(
        f"{API}/interior-walkthrough/steps/{first.json()['id']}",
        json={"position": 1, "room_id": None},
    )

    walkthrough = client.get(f"{API}/interior-walkthrough?project_id={project_id}").json()

    assert [(step["title"], step["room_id"]) for step in walkthrough["steps"]] == [
        ("Habitación principal", None),
        ("Sala / Comedor", None),
    ]
    assert walkthrough["steps"][1]["view_config"] == {"cut_fraction": 0.8}
    assert walkthrough["renovation_logs"] == []

    assert (
        client.delete(f"{API}/interior-walkthrough/steps/{first.json()['id']}").status_code == 204
    )
    assert (
        len(client.get(f"{API}/interior-walkthrough?project_id={project_id}").json()["steps"]) == 1
    )


def test_renovation_logs_follow_the_work(client, project_id, room_id):
    created = client.post(
        f"{API}/interior-walkthrough/logs",
        json={
            "project_id": project_id,
            "room_id": room_id,
            "layer": "finishes",
            "title": "Lay the wooden floor",
            "planned_start": "2026-11-16",
            "planned_end": "2026-11-20",
            "estimated_cost": 2400,
        },
    )

    assert created.status_code == 201
    log = created.json()
    assert (log["status"], log["completed_at"], log["estimated_cost"]) == ("planned", None, 2400)
    assert log["created_by"] is not None

    url = f"{API}/interior-walkthrough/logs/{log['id']}"
    done = client.patch(url, json={"status": "completed"}).json()

    assert done["completed_at"] is not None
    assert client.patch(url, json={"status": "in_progress"}).json()["completed_at"] is None

    late = client.patch(url, json={"planned_end": "2026-11-01"})

    assert late.status_code == 422
    assert late.json()["detail"] == "La fecha de fin no puede ser anterior a la fecha de inicio."
    assert client.patch(url, json={"planned_start": None}).json()["planned_end"] == "2026-11-20"

    listing = f"{API}/interior-walkthrough/logs?project_id={project_id}"

    assert len(client.get(f"{listing}&status=in_progress").json()) == 1
    assert client.get(f"{listing}&status=planned").json() == []
    assert len(client.get(f"{listing}&room_id={room_id}").json()) == 1
    assert client.delete(url).status_code == 204
    assert client.get(listing).json() == []


def test_renovation_logs_validate_their_dates_and_links(client, project_id):
    def add(**extra):
        return client.post(
            f"{API}/interior-walkthrough/logs",
            json={"project_id": project_id, "layer": "structure", "title": "Work", **extra},
        )

    backwards = add(planned_start="2026-11-20", planned_end="2026-11-16")

    assert backwards.status_code == 422
    assert backwards.json()["detail"][0]["msg"] == (
        "La fecha de fin no puede ser anterior a la fecha de inicio."
    )
    assert add(planned_start="soon").json()["detail"][0]["msg"] == (
        "Debe ser una fecha con formato AAAA-MM-DD."
    )
    assert add(room_id=9999).status_code == 404
    assert add(spatial_element_id=9999).status_code == 404
    assert add(layer="roof").status_code == 422
    assert add(status="completed").json()["completed_at"] is not None


def test_other_users_cannot_reach_spatial_data_or_walkthroughs(
    client, project_id, room_id, stranger
):
    element_id = client.post(
        f"{API}/spatial-data/elements", json={**ELEMENT, "project_id": project_id}
    ).json()["id"]
    step_id = client.post(
        f"{API}/interior-walkthrough/steps", json={"project_id": project_id, "title": "Step"}
    ).json()["id"]
    log_id = client.post(
        f"{API}/interior-walkthrough/logs",
        json={"project_id": project_id, "layer": "structure", "title": "Work"},
    ).json()["id"]

    for path in (
        f"{API}/spatial-data?project_id={project_id}",
        f"{API}/spatial-data/elements/{element_id}",
        f"{API}/interior-walkthrough?project_id={project_id}",
        f"{API}/interior-walkthrough/logs?project_id={project_id}",
        f"{API}/rooms?project_id={project_id}",
        f"{API}/rooms/{room_id}",
    ):
        assert stranger.get(path).status_code == 404, path

    for path in (
        f"{API}/spatial-data/elements/{element_id}",
        f"{API}/interior-walkthrough/steps/{step_id}",
        f"{API}/interior-walkthrough/logs/{log_id}",
        f"{API}/rooms/{room_id}",
    ):
        assert stranger.patch(path, json={}).status_code == 404, path

    assert stranger.delete(f"{API}/interior-walkthrough/steps/{step_id}").status_code == 404
    assert stranger.delete(f"{API}/interior-walkthrough/logs/{log_id}").status_code == 404
    assert (
        stranger.post(
            f"{API}/spatial-data/import",
            json={"project_id": project_id, "provider": "native", "document": {"elements": []}},
        ).status_code
        == 404
    )
