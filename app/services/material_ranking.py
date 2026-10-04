from collections.abc import Iterable

from app.data_structures import DynamicArray
from app.models import Material


def total_cost(material: Material):
    return material.quantity * material.unit_cost


def rank_by_cost(materials: Iterable[Material]) -> DynamicArray[Material]:
    ranked: DynamicArray[Material] = DynamicArray()

    for material in materials:
        position = 0

        while position < len(ranked) and total_cost(ranked[position]) >= total_cost(
            material
        ):
            position += 1

        ranked.insert_at(position, material)

    return ranked
