PASSWORD = "correct-horse-battery"


def register(client, name="Ana", email="ana@example.com", password=PASSWORD):
    response = client.post(
        "/auth/register", json={"name": name, "email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    return response.json()
