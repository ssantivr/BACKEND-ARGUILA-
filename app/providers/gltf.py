from itertools import product
from typing import Any

from app.providers.base import ElementDraft, Point, ProviderDataError
from app.providers.native import read_point

Matrix = list[list[float]]

IDENTITY: Matrix = [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]
MAX_DEPTH = 64


def multiply(left: Matrix, right: Matrix) -> Matrix:
    return [
        [sum(left[row][k] * right[k][column] for k in range(4)) for column in range(4)]
        for row in range(4)
    ]


def transform(matrix: Matrix, point: Point) -> Point:
    x, y, z = point

    return (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    )


def numbers(value: Any, length: int, default: list[float], label: str) -> list[float]:
    if value is None:
        return default

    if (
        not isinstance(value, list)
        or len(value) != length
        or not all(isinstance(item, int | float) and not isinstance(item, bool) for item in value)
    ):
        raise ProviderDataError(f"{label} debe ser una lista de {length} números.")

    return [float(item) for item in value]


def local_matrix(node: dict[str, Any], label: str) -> Matrix:
    if "matrix" in node:
        flat = numbers(node["matrix"], 16, [], f"{label}.matrix")

        # glTF stores matrices in column-major order.
        return [[flat[column * 4 + row] for column in range(4)] for row in range(4)]

    tx, ty, tz = numbers(node.get("translation"), 3, [0, 0, 0], f"{label}.translation")
    sx, sy, sz = numbers(node.get("scale"), 3, [1, 1, 1], f"{label}.scale")
    x, y, z, w = numbers(node.get("rotation"), 4, [0, 0, 0, 1], f"{label}.rotation")

    return [
        [(1 - 2 * (y * y + z * z)) * sx, 2 * (x * y - z * w) * sy, 2 * (x * z + y * w) * sz, tx],
        [2 * (x * y + z * w) * sx, (1 - 2 * (x * x + z * z)) * sy, 2 * (y * z - x * w) * sz, ty],
        [2 * (x * z - y * w) * sx, 2 * (y * z + x * w) * sy, (1 - 2 * (x * x + y * y)) * sz, tz],
        [0.0, 0.0, 0.0, 1.0],
    ]


def to_plan(point: Point) -> Point:
    # glTF is right-handed with +Y up; ARQUILA draws the plan on x and y and raises z.
    x, y, z = point

    return x, -z, y


def items(document: dict[str, Any], key: str) -> list[Any]:
    value = document.get(key, [])

    if not isinstance(value, list):
        raise ProviderDataError(f"«{key}» debe ser una lista.")

    return value


class GltfAdapter:
    """Reads the JSON part of a glTF 2.0 asset: one element per node that has a mesh.

    The bounds come from the POSITION accessors, whose min and max the format requires,
    so no binary buffer is needed.
    """

    name = "gltf"

    def read(self, document: dict[str, Any]) -> list[ElementDraft]:
        version = str((document.get("asset") or {}).get("version", ""))

        if not version.startswith("2."):
            raise ProviderDataError("Solo se admite glTF 2.0 (falta «asset.version»).")

        nodes = items(document, "nodes")
        meshes = items(document, "meshes")
        accessors = items(document, "accessors")
        drafts: list[ElementDraft] = []
        visited = 0

        def visit(index: Any, parent: Matrix, depth: int) -> None:
            nonlocal visited
            visited += 1

            # A valid glTF visits each node once; more visits mean a cycle or a shared node.
            if (
                not isinstance(index, int)
                or not 0 <= index < len(nodes)
                or depth > MAX_DEPTH
                or visited > len(nodes)
            ):
                raise ProviderDataError("La jerarquía de nodos del glTF no es válida.")

            node = nodes[index]

            if not isinstance(node, dict):
                raise ProviderDataError(f"nodes[{index}] debe ser un objeto.")

            world = multiply(parent, local_matrix(node, f"nodes[{index}]"))

            if "mesh" in node:
                drafts.append(self._draft(node, index, world, meshes, accessors))

            for child in node.get("children") or []:
                visit(child, world, depth + 1)

        for root in self._roots(document, len(nodes)):
            visit(root, IDENTITY, 0)

        return drafts

    def _roots(self, document: dict[str, Any], node_count: int) -> list[Any]:
        scenes = items(document, "scenes")

        if not scenes:
            return list(range(node_count))

        index = document.get("scene", 0)

        if not isinstance(index, int) or not 0 <= index < len(scenes):
            raise ProviderDataError("«scene» no apunta a una escena del documento.")

        return list(scenes[index].get("nodes") or [])

    def _draft(
        self,
        node: dict[str, Any],
        index: int,
        world: Matrix,
        meshes: list[Any],
        accessors: list[Any],
    ) -> ElementDraft:
        mesh_index = node["mesh"]

        if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
            raise ProviderDataError(f"nodes[{index}].mesh no apunta a una malla del documento.")

        mesh = meshes[mesh_index] or {}
        corners: list[Point] = []

        for primitive in mesh.get("primitives") or []:
            position = (primitive.get("attributes") or {}).get("POSITION")

            if not isinstance(position, int) or not 0 <= position < len(accessors):
                raise ProviderDataError(
                    f"meshes[{mesh_index}] tiene una primitiva sin atributo POSITION."
                )

            label = f"accessors[{position}]"
            low = read_point(accessors[position].get("min"), f"{label}.min")
            high = read_point(accessors[position].get("max"), f"{label}.max")

            corners.extend(
                to_plan(transform(world, (x, y, z)))
                for x, y, z in product(*zip(low, high, strict=True))
            )

        if not corners:
            raise ProviderDataError(f"meshes[{mesh_index}] no tiene geometría.")

        extras = node.get("extras") if isinstance(node.get("extras"), dict) else {}
        name = str(node.get("name") or mesh.get("name") or f"Nodo {index}")

        return ElementDraft(
            external_id=f"node-{index}",
            name=name,
            minimum=tuple(min(corner[axis] for corner in corners) for axis in range(3)),
            maximum=tuple(max(corner[axis] for corner in corners) for axis in range(3)),
            kind=str(extras.get("kind") or "mesh"),
            layer=extras.get("layer"),
            work_status=extras.get("work_status"),
            mesh_ref=f"meshes/{mesh_index}",
            config={"gltf_node": index},
        )
