from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SESSION_COOKIE
from app.main import app
from app.services import auth_service
from tests.helpers import PASSWORD, register

PNG = b"\x89PNG\r\n\x1a\n" + b"fake image data"


def login(client, email="ana@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_register_logs_the_user_in(client):
    user = register(client)

    assert user["email"] == "ana@example.com"
    assert "password" not in user and "password_hash" not in user
    assert client.get("/auth/me").json() == user


def test_session_cookie_is_http_only(client):
    response = client.post(
        "/auth/register",
        json={"name": "Ana", "email": "ana@example.com", "password": PASSWORD},
    )

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Ana", "email": "ana@example.com", "password": "short"},
        {"name": "Ana", "email": "not-an-email", "password": PASSWORD},
        {"name": "", "email": "ana@example.com", "password": PASSWORD},
        {"name": "Ana", "email": "ana@example.com"},
    ],
)
def test_invalid_registration_is_rejected(client, payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_duplicate_email_is_rejected_ignoring_case(client):
    register(client)

    response = client.post(
        "/auth/register",
        json={"name": "Other", "email": "ANA@Example.com", "password": PASSWORD},
    )

    assert response.status_code == 409


def test_login_and_logout(client):
    user = register(client)

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401

    response = login(client, email="  ANA@example.com ")
    assert response.status_code == 200
    assert response.json() == user
    assert client.get("/auth/me").json() == user


def test_wrong_credentials_get_the_same_error(client):
    register(client)
    client.post("/auth/logout")

    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert client.get("/auth/me").status_code == 401


def test_logout_invalidates_the_token_on_the_server(client):
    register(client)
    token = client.cookies.get(SESSION_COOKIE)

    client.post("/auth/logout")
    client.cookies.set(SESSION_COOKIE, token)

    assert client.get("/auth/me").status_code == 401


def test_forged_or_expired_sessions_are_rejected(client, monkeypatch):
    client.cookies.set(SESSION_COOKIE, "not-a-real-token")
    assert client.get("/auth/me").status_code == 401
    client.cookies.clear()

    monkeypatch.setattr(auth_service, "SESSION_LIFETIME", timedelta(seconds=-1))
    register(client)

    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/projects"),
        ("post", "/projects"),
        ("get", "/projects/1"),
        ("delete", "/projects/1"),
        ("get", "/projects/1/terrains"),
        ("get", "/terrains/1"),
        ("get", "/projects/1/materials"),
        ("get", "/projects/1/plans"),
        ("get", "/projects/1/elevations"),
        ("get", "/projects/1/recommendations"),
        ("post", "/projects/1/recommendations/generate"),
        ("get", "/projects/1/files"),
        ("get", "/files/1/content"),
        ("get", "/projects/1/undo"),
        ("post", "/projects/1/undo"),
    ],
)
def test_endpoints_require_authentication(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_users_cannot_reach_each_others_data(client):
    register(client)
    project = client.post("/projects", json={"name": "Demo House"}).json()["id"]
    base = f"/projects/{project}"

    terrain = client.post(f"{base}/terrains", json={"name": "Lot", "area_m2": 100}).json()["id"]
    material = client.post(f"{base}/materials", json={"name": "Brick", "unit": "u"}).json()["id"]
    plan = client.post(f"{base}/plans", json={"title": "Ground"}).json()["id"]
    elevation = client.post(
        f"{base}/elevations", json={"title": "Front", "orientation": "north"}
    ).json()["id"]
    recommendation = client.post(
        f"{base}/recommendations", json={"category": "design", "content": "Keep the tree."}
    ).json()["id"]
    file = client.post(f"{base}/files", files={"file": ("a.png", PNG, "image/png")}).json()["id"]

    intruder = TestClient(app)
    register(intruder, name="Eve", email="eve@example.com")

    assert intruder.get("/projects").json() == []

    for path in (
        base,
        f"{base}/terrains",
        f"{base}/materials",
        f"{base}/plans",
        f"{base}/elevations",
        f"{base}/recommendations",
        f"{base}/files",
        f"{base}/undo",
        f"/terrains/{terrain}",
        f"/materials/{material}",
        f"/plans/{plan}",
        f"/elevations/{elevation}",
        f"/files/{file}",
        f"/files/{file}/content",
    ):
        assert intruder.get(path).status_code == 404, path

    assert intruder.patch(base, json={"name": "Stolen"}).status_code == 404
    assert intruder.patch(f"/terrains/{terrain}", json={"name": "x"}).status_code == 404
    assert intruder.patch(f"/plans/{plan}", json={"title": "x"}).status_code == 404
    assert intruder.post(f"{base}/terrains", json={"name": "x", "area_m2": 1}).status_code == 404
    assert intruder.post(f"{base}/recommendations/generate").status_code == 404
    assert intruder.post(f"{base}/undo").status_code == 404

    for path in (
        f"/terrains/{terrain}",
        f"/materials/{material}",
        f"/plans/{plan}",
        f"/elevations/{elevation}",
        f"/recommendations/{recommendation}",
        f"/files/{file}",
        base,
    ):
        assert intruder.delete(path).status_code == 404, path

    # The intruder cannot attach the owner's file to their own plan either.
    own = intruder.post("/projects", json={"name": "Mine"}).json()["id"]
    attach = intruder.post(f"/projects/{own}/plans", json={"title": "P", "file_id": file})
    assert attach.status_code == 404

    # Nothing changed for the owner.
    assert client.get(base).json()["name"] == "Demo House"
    assert len(client.get(f"{base}/terrains").json()) == 1
    assert client.get(f"/files/{file}/content").content == PNG


def test_two_users_can_use_the_same_project_name(client):
    register(client)
    assert client.post("/projects", json={"name": "Demo House"}).status_code == 201

    other = TestClient(app)
    register(other, name="Eve", email="eve@example.com")

    assert other.post("/projects", json={"name": "Demo House"}).status_code == 201
