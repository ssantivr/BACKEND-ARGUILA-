import pytest

from app.services.geometry import polygon_area
from tests.helpers import register

L_SHAPE = [
    {"x_m": 0, "y_m": 0},
    {"x_m": 20, "y_m": 0},
    {"x_m": 20, "y_m": 10},
    {"x_m": 10, "y_m": 10},
    {"x_m": 10, "y_m": 30},
    {"x_m": 0, "y_m": 30},
]


@pytest.fixture
def project_id(client):
    register(client)
    return client.post("/projects", json={"name": "Demo House"}).json()["id"]


def create(client, project_id, **fields):
    payload = {"name": "Corner Lot", "area_m2": 400, **fields}
    return client.post(f"/projects/{project_id}/terrains", json=payload)


def test_polygon_area_uses_the_shoelace_formula():
    assert polygon_area([(0, 0), (4, 0), (4, 3), (0, 3)]) == 12
    assert polygon_area([(0, 3), (4, 3), (4, 0), (0, 0)]) == 12
    assert polygon_area([(p["x_m"], p["y_m"]) for p in L_SHAPE]) == 400
    assert polygon_area([(0, 0), (5, 5), (10, 10)]) == 0


def test_polygon_area_of_fewer_than_three_points_is_zero():
    assert polygon_area([]) == 0
    assert polygon_area([(3, 4)]) == 0
    assert polygon_area([(0, 0), (5, 5)]) == 0


def test_terrain_without_points_has_an_empty_list(client, project_id):
    assert create(client, project_id).json()["points"] == []


def test_points_are_stored_in_order(client, project_id):
    response = create(client, project_id, points=L_SHAPE)

    assert response.status_code == 201
    terrain = response.json()
    assert terrain["points"] == L_SHAPE
    assert client.get(f"/terrains/{terrain['id']}").json()["points"] == L_SHAPE


def test_points_can_be_replaced_and_removed(client, project_id):
    terrain_id = create(client, project_id, points=L_SHAPE).json()["id"]
    triangle = [{"x_m": 0, "y_m": 0}, {"x_m": 12.5, "y_m": 0}, {"x_m": 0, "y_m": 8}]

    replaced = client.patch(f"/terrains/{terrain_id}", json={"points": triangle})
    assert replaced.status_code == 200
    assert replaced.json()["points"] == triangle

    untouched = client.patch(f"/terrains/{terrain_id}", json={"name": "Renamed"})
    assert untouched.json()["points"] == triangle

    removed = client.patch(f"/terrains/{terrain_id}", json={"points": None})
    assert removed.json()["points"] == []
    assert removed.json()["name"] == "Renamed"


@pytest.mark.parametrize(
    "points",
    [
        [{"x_m": 0, "y_m": 0}, {"x_m": 5, "y_m": 0}],
        [{"x_m": 0, "y_m": 0}, {"x_m": 5, "y_m": 5}, {"x_m": 10, "y_m": 10}],
        [{"x_m": 0, "y_m": 0}, {"x_m": 5, "y_m": 0}, {"x_m": 5}],
        [{"x_m": i, "y_m": i * i} for i in range(51)],
    ],
)
def test_invalid_polygons_are_rejected(client, project_id, points):
    assert create(client, project_id, points=points).status_code == 422


def test_deleting_the_terrain_removes_its_points(client, project_id):
    terrain_id = create(client, project_id, points=L_SHAPE).json()["id"]

    assert client.delete(f"/terrains/{terrain_id}").status_code == 204
    assert client.get(f"/terrains/{terrain_id}").status_code == 404

    again = create(client, project_id, points=L_SHAPE)
    assert again.status_code == 201
    assert again.json()["points"] == L_SHAPE
