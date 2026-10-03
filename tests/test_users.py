def test_create_and_get_user(client):
    response = client.post("/users", json={"name": "Ana", "email": "ana@example.com"})

    assert response.status_code == 201
    user = response.json()
    assert user["name"] == "Ana"

    assert client.get(f"/users/{user['id']}").json() == user
    assert client.get("/users").json() == [user]


def test_duplicate_email_is_rejected(client):
    payload = {"name": "Ana", "email": "ana@example.com"}
    client.post("/users", json=payload)

    assert client.post("/users", json=payload).status_code == 409


def test_invalid_email_is_rejected(client):
    response = client.post("/users", json={"name": "Ana", "email": "not-an-email"})

    assert response.status_code == 422


def test_unknown_user_returns_404(client):
    assert client.get("/users/999").status_code == 404
