import base64
import struct
from dataclasses import dataclass
from typing import Any, Protocol

Point = tuple[float, float, float]

ROOM_LAYER = "room"
LAYER_COLORS = {
    ROOM_LAYER: [0.72, 0.75, 0.78, 0.35],
    "structure": [0.0, 0.94, 1.0, 1.0],
    "installations": [1.0, 0.0, 0.5, 1.0],
    "finishes": [1.0, 0.78, 0.34, 1.0],
}
CUBE_CORNERS = [(x, y, z) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
CUBE_TRIANGLES = [
    (0, 1, 3, 0, 3, 2),
    (4, 6, 7, 4, 7, 5),
    (0, 4, 5, 0, 5, 1),
    (2, 3, 7, 2, 7, 6),
    (0, 2, 6, 0, 6, 4),
    (1, 5, 7, 1, 7, 3),
]
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963
FLOAT = 5126
UNSIGNED_SHORT = 5123


@dataclass(frozen=True)
class Box:
    """An axis-aligned volume in ARQUILA coordinates: metres, x and y on the plan, z upwards."""

    name: str
    layer: str
    kind: str
    minimum: Point
    maximum: Point


class SceneEncoder(Protocol):
    """Implementation side of the bridge: how a list of boxes becomes a document."""

    media_type: str

    def encode(self, title: str, boxes: list[Box]) -> dict[str, Any]: ...


class JsonSceneEncoder:
    media_type = "application/json"

    def encode(self, title: str, boxes: list[Box]) -> dict[str, Any]:
        return {
            "title": title,
            "units": "m",
            "up_axis": "z",
            "boxes": [
                {
                    "name": box.name,
                    "layer": box.layer,
                    "kind": box.kind,
                    "min": list(box.minimum),
                    "max": list(box.maximum),
                }
                for box in boxes
            ],
        }


class GltfSceneEncoder:
    """Writes a self-contained glTF 2.0 document: one unit cube, placed once per box."""

    media_type = "model/gltf+json"

    def encode(self, title: str, boxes: list[Box]) -> dict[str, Any]:
        layers = sorted({box.layer for box in boxes})
        positions = b"".join(struct.pack("<3f", *corner) for corner in CUBE_CORNERS)
        indices = b"".join(struct.pack("<6H", *face) for face in CUBE_TRIANGLES)
        data = base64.b64encode(positions + indices).decode("ascii")

        return {
            "asset": {"version": "2.0", "generator": "ARQUILA"},
            "scene": 0,
            "scenes": [{"name": title, "nodes": list(range(len(boxes)))}],
            "nodes": [self._node(box, layers.index(box.layer)) for box in boxes],
            "meshes": [
                {
                    "name": layer,
                    "primitives": [
                        {"attributes": {"POSITION": 0}, "indices": 1, "material": index}
                    ],
                }
                for index, layer in enumerate(layers)
            ],
            "materials": [self._material(layer) for layer in layers],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": FLOAT,
                    "count": len(CUBE_CORNERS),
                    "type": "VEC3",
                    "min": [-0.5, -0.5, -0.5],
                    "max": [0.5, 0.5, 0.5],
                },
                {
                    "bufferView": 1,
                    "componentType": UNSIGNED_SHORT,
                    "count": len(CUBE_TRIANGLES) * 6,
                    "type": "SCALAR",
                },
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(positions),
                    "target": ARRAY_BUFFER,
                },
                {
                    "buffer": 0,
                    "byteOffset": len(positions),
                    "byteLength": len(indices),
                    "target": ELEMENT_ARRAY_BUFFER,
                },
            ],
            "buffers": [
                {
                    "byteLength": len(positions) + len(indices),
                    "uri": f"data:application/octet-stream;base64,{data}",
                }
            ],
        }

    def _node(self, box: Box, mesh: int) -> dict[str, Any]:
        (min_x, min_y, min_z), (max_x, max_y, max_z) = box.minimum, box.maximum

        # glTF is right-handed with +Y up, so the plan's y becomes -z.
        return {
            "name": box.name,
            "mesh": mesh,
            "translation": [(min_x + max_x) / 2, (min_z + max_z) / 2, -(min_y + max_y) / 2],
            "scale": [max_x - min_x, max_z - min_z, max_y - min_y],
            "extras": {"layer": box.layer, "kind": box.kind},
        }

    def _material(self, layer: str) -> dict[str, Any]:
        color = LAYER_COLORS.get(layer, LAYER_COLORS[ROOM_LAYER])
        material: dict[str, Any] = {
            "name": layer,
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": 0.0,
                "roughnessFactor": 0.6,
            },
        }

        if color[3] < 1:
            material["alphaMode"] = "BLEND"

        return material


ENCODERS: dict[str, SceneEncoder] = {"json": JsonSceneEncoder(), "gltf": GltfSceneEncoder()}
