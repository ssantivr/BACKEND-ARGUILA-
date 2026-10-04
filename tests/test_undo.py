import pytest

from tests.helpers import register

from app.services.undo_history import DeletedRecord, UndoHistory


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post(
        "/projects", json={"name": "Demo House"}
    )
    return project.json()["id"]


def add(client, project_id, resource, payload):
    response = client.post(f"/projects/{project_id}/{resource}", json=payload)
    assert response.status_code == 201
    return response.json()


def add_material(client, project_id, name="Concrete"):
    payload = {"name": name, "category": "structure", "unit": "m3", "quantity": 85, "unit_cost": 110.25}
    return add(client, project_id, "materials", payload)


def history(client, project_id):
    return client.get(f"/projects/{project_id}/undo").json()


def undo(client, project_id):
    return client.post(f"/projects/{project_id}/undo")


def test_undo_restores_a_deleted_material_with_its_data(client, project_id):
    material = add_material(client, project_id)
    client.delete(f"/materials/{material['id']}")

    assert history(client, project_id) == [{"kind": "material", "label": "Concrete"}]

    response = undo(client, project_id)

    assert response.status_code == 200
    assert response.json() == {"kind": "material", "label": "Concrete"}
    assert history(client, project_id) == []

    [restored] = client.get(f"/projects/{project_id}/materials").json()
    for field in ("name", "category", "unit", "quantity", "unit_cost", "created_at"):
        assert restored[field] == material[field]


def test_undo_is_last_in_first_out_across_resource_types(client, project_id):
    terrain = add(client, project_id, "terrains", {"name": "Main Lot", "area_m2": 450})
    plan = add(client, project_id, "plans", {"title": "Ground floor"})
    elevation = add(
        client, project_id, "elevations", {"title": "Front", "orientation": "north"}
    )

    client.delete(f"/terrains/{terrain['id']}")
    client.delete(f"/plans/{plan['id']}")
    client.delete(f"/elevations/{elevation['id']}")

    assert [item["kind"] for item in history(client, project_id)] == [
        "elevation",
        "plan",
        "terrain",
    ]

    assert undo(client, project_id).json()["kind"] == "elevation"
    assert undo(client, project_id).json()["kind"] == "plan"
    assert len(client.get(f"/projects/{project_id}/elevations").json()) == 1
    assert len(client.get(f"/projects/{project_id}/plans").json()) == 1
    assert client.get(f"/projects/{project_id}/terrains").json() == []

    assert undo(client, project_id).json() == {"kind": "terrain", "label": "Main Lot"}
    [restored] = client.get(f"/projects/{project_id}/terrains").json()
    assert restored["area_m2"] == 450


def test_undo_with_empty_history_returns_404(client, project_id):
    assert undo(client, project_id).status_code == 404
    assert undo(client, 999).status_code == 404
    assert client.get("/projects/999/undo").status_code == 404


def test_undo_conflict_keeps_the_entry_in_history(client, project_id):
    material = add_material(client, project_id)
    client.delete(f"/materials/{material['id']}")
    replacement = add_material(client, project_id)

    assert undo(client, project_id).status_code == 409
    assert history(client, project_id) == [{"kind": "material", "label": "Concrete"}]

    client.patch(f"/materials/{replacement['id']}", json={"name": "Concrete B"})

    assert undo(client, project_id).status_code == 200
    names = [m["name"] for m in client.get(f"/projects/{project_id}/materials").json()]
    assert sorted(names) == ["Concrete", "Concrete B"]


def test_history_is_separate_per_project_and_dropped_with_the_project(client, project_id):
    other = client.post("/projects", json={"name": "Other"}).json()["id"]
    material = add_material(client, project_id)
    client.delete(f"/materials/{material['id']}")

    assert history(client, other) == []
    assert undo(client, other).status_code == 404
    assert len(history(client, project_id)) == 1

    client.delete(f"/projects/{project_id}")
    recreated = client.post("/projects", json={"name": "Demo House"}).json()

    assert history(client, recreated["id"]) == []


def redo(client, project_id):
    return client.post(f"/projects/{project_id}/redo")


def test_redo_deletes_again_what_undo_restored(client, project_id):
    material = add_material(client, project_id)
    client.delete(f"/materials/{material['id']}")
    undo(client, project_id)

    response = redo(client, project_id)

    assert response.status_code == 200
    assert response.json() == {"kind": "material", "label": "Concrete"}
    assert client.get(f"/projects/{project_id}/materials").json() == []
    assert history(client, project_id) == [{"kind": "material", "label": "Concrete"}]

    assert undo(client, project_id).status_code == 200
    assert len(client.get(f"/projects/{project_id}/materials").json()) == 1


def test_redo_is_last_in_first_out(client, project_id):
    first = add_material(client, project_id, "Concrete")
    second = add_material(client, project_id, "Steel")
    client.delete(f"/materials/{first['id']}")
    client.delete(f"/materials/{second['id']}")

    assert undo(client, project_id).json()["label"] == "Steel"
    assert undo(client, project_id).json()["label"] == "Concrete"

    assert redo(client, project_id).json()["label"] == "Concrete"
    assert redo(client, project_id).json()["label"] == "Steel"
    assert redo(client, project_id).status_code == 404


def test_redo_with_nothing_restored_returns_404(client, project_id):
    assert redo(client, project_id).status_code == 404
    assert redo(client, 999).status_code == 404


def test_a_new_deletion_discards_what_could_be_redone(client, project_id):
    first = add_material(client, project_id, "Concrete")
    second = add_material(client, project_id, "Steel")
    client.delete(f"/materials/{first['id']}")
    undo(client, project_id)

    client.delete(f"/materials/{second['id']}")

    assert redo(client, project_id).status_code == 404
    names = [m["name"] for m in client.get(f"/projects/{project_id}/materials").json()]
    assert names == ["Concrete"]


def record(project_id: int, label: str) -> DeletedRecord:
    return DeletedRecord(project_id, "material", label, object, {})


def test_history_drops_the_oldest_entry_when_full():
    undo_history = UndoHistory(capacity=3)

    for label in ("a", "b", "c", "d"):
        undo_history.record(record(1, label))

    assert [entry.label for entry in undo_history.list(1)] == ["d", "c", "b"]
    assert undo_history.pop_last(1).label == "d"
    assert undo_history.pop_last(1).label == "c"
    assert undo_history.pop_last(1).label == "b"
    assert undo_history.pop_last(1) is None
    assert undo_history.pop_last(2) is None
