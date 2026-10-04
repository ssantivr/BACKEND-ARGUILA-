import pytest

from app import storage
from tests.helpers import register

PNG = b"\x89PNG\r\n\x1a\n" + b"fake image data"
PDF = b"%PDF-1.7\nfake document"


@pytest.fixture
def project_id(client):
    register(client)
    project = client.post("/projects", json={"name": "Demo House"})
    return project.json()["id"]


def upload(client, project_id, name="plan.png", content=PNG, declared="image/png"):
    return client.post(f"/projects/{project_id}/files", files={"file": (name, content, declared)})


def stored_files(tmp_path):
    directory = tmp_path / "uploads"
    return sorted(directory.iterdir()) if directory.exists() else []


def test_upload_list_and_download(client, project_id, tmp_path):
    response = upload(client, project_id)

    assert response.status_code == 201
    file = response.json()
    assert file["filename"] == "plan.png"
    assert file["mime_type"] == "image/png"
    assert file["size_bytes"] == len(PNG)
    assert "storage_path" not in file

    assert client.get(f"/files/{file['id']}").json() == file
    assert client.get(f"/projects/{project_id}/files").json() == [file]

    content = client.get(f"/files/{file['id']}/content")
    assert content.status_code == 200
    assert content.content == PNG
    assert content.headers["content-type"] == "image/png"
    assert content.headers["x-content-type-options"] == "nosniff"

    assert len(stored_files(tmp_path)) == 1


def test_type_comes_from_the_content_not_from_the_client(client, project_id):
    response = upload(client, project_id, name="doc.png", content=PDF, declared="image/png")

    assert response.status_code == 201
    assert response.json()["mime_type"] == "application/pdf"


@pytest.mark.parametrize("content", [b"", b"<html><script>alert(1)</script>", b"MZ\x90\x00"])
def test_unsupported_content_is_rejected(client, project_id, tmp_path, content):
    response = upload(client, project_id, name="plan.png", content=content)

    assert response.status_code == 415
    assert stored_files(tmp_path) == []
    assert client.get(f"/projects/{project_id}/files").json() == []


def test_file_over_the_size_limit_is_rejected(client, project_id, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "MAX_FILE_BYTES", 32)

    response = upload(client, project_id, content=PNG + b"x" * 64)

    assert response.status_code == 413
    assert stored_files(tmp_path) == []


def test_client_path_is_not_used_for_storage(client, project_id, tmp_path):
    response = upload(client, project_id, name="..\\..\\evil/../../plan.png")

    assert response.status_code == 201
    assert response.json()["filename"] == "plan.png"

    [stored] = stored_files(tmp_path)
    assert stored.parent == tmp_path / "uploads"
    assert stored.suffix == ".png"
    assert "plan" not in stored.name


def test_requires_existing_project_and_file(client):
    register(client)

    assert upload(client, 999).status_code == 404
    assert client.get("/projects/999/files").status_code == 404
    assert client.get("/files/999").status_code == 404
    assert client.get("/files/999/content").status_code == 404
    assert client.delete("/files/999").status_code == 404


def test_attach_and_detach_file_on_plan_and_elevation(client, project_id):
    file_id = upload(client, project_id).json()["id"]

    plan = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "file_id": file_id}
    ).json()
    assert plan["file_id"] == file_id

    elevation = client.post(
        f"/projects/{project_id}/elevations", json={"title": "Front", "orientation": "north"}
    ).json()
    attached = client.patch(f"/elevations/{elevation['id']}", json={"file_id": file_id})
    assert attached.json()["file_id"] == file_id
    assert attached.json()["orientation"] == "north"

    detached = client.patch(f"/plans/{plan['id']}", json={"file_id": None})
    assert detached.json()["file_id"] is None
    assert detached.json()["title"] == "Ground floor"


def test_cannot_attach_a_file_from_another_project(client, project_id):
    other = client.post("/projects", json={"name": "Other"}).json()["id"]
    foreign_file = upload(client, other).json()["id"]
    plan = client.post(f"/projects/{project_id}/plans", json={"title": "Ground"}).json()

    assert client.patch(f"/plans/{plan['id']}", json={"file_id": foreign_file}).status_code == 404
    assert client.patch(f"/plans/{plan['id']}", json={"file_id": 999}).status_code == 404

    created = client.post(
        f"/projects/{project_id}/elevations",
        json={"title": "Front", "orientation": "north", "file_id": foreign_file},
    )
    assert created.status_code == 404


def test_deleting_a_file_detaches_it_and_removes_it_from_disk(client, project_id, tmp_path):
    file_id = upload(client, project_id).json()["id"]
    plan = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "file_id": file_id}
    ).json()

    assert client.delete(f"/files/{file_id}").status_code == 204

    assert stored_files(tmp_path) == []
    assert client.get(f"/files/{file_id}/content").status_code == 404
    assert client.get(f"/plans/{plan['id']}").json()["file_id"] is None


def test_deleting_a_project_removes_its_files_from_disk(client, project_id, tmp_path):
    upload(client, project_id)
    upload(client, project_id, name="b.pdf", content=PDF)
    assert len(stored_files(tmp_path)) == 2

    client.delete(f"/projects/{project_id}")

    assert stored_files(tmp_path) == []


def test_undo_restores_a_plan_without_a_file_deleted_in_between(client, project_id):
    file_id = upload(client, project_id).json()["id"]
    plan = client.post(
        f"/projects/{project_id}/plans", json={"title": "Ground floor", "file_id": file_id}
    ).json()

    client.delete(f"/plans/{plan['id']}")
    client.delete(f"/files/{file_id}")

    assert client.post(f"/projects/{project_id}/undo").status_code == 200
    [restored] = client.get(f"/projects/{project_id}/plans").json()
    assert restored["title"] == "Ground floor"
    assert restored["file_id"] is None


def test_content_missing_from_disk_is_not_found(client, project_id, tmp_path):
    file_id = upload(client, project_id).json()["id"]

    for path in stored_files(tmp_path):
        path.unlink()

    assert client.get(f"/files/{file_id}").status_code == 200
    assert client.get(f"/files/{file_id}/content").status_code == 404
