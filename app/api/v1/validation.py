from typing import Any

MESSAGES = {
    "missing": "Este campo es obligatorio.",
    "string_too_short": "Debe tener al menos {min_length} caracteres.",
    "string_too_long": "Debe tener como máximo {max_length} caracteres.",
    "string_pattern_mismatch": "No tiene el formato esperado.",
    "string_type": "Debe ser un texto.",
    "greater_than": "Debe ser mayor que {gt}.",
    "greater_than_equal": "Debe ser mayor o igual que {ge}.",
    "less_than": "Debe ser menor que {lt}.",
    "less_than_equal": "Debe ser menor o igual que {le}.",
    "too_short": "Debe tener al menos {min_length} elementos.",
    "int_type": "Debe ser un número entero.",
    "int_parsing": "Debe ser un número entero.",
    "int_from_float": "Debe ser un número entero.",
    "float_type": "Debe ser un número.",
    "float_parsing": "Debe ser un número.",
    "bool_type": "Debe ser verdadero o falso.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "date_type": "Debe ser una fecha con formato AAAA-MM-DD.",
    "date_parsing": "Debe ser una fecha con formato AAAA-MM-DD.",
    "date_from_datetime_parsing": "Debe ser una fecha con formato AAAA-MM-DD.",
    "date_from_datetime_inexact": "Debe ser una fecha con formato AAAA-MM-DD.",
    "literal_error": "Valor no permitido. Opciones: {expected}.",
    "dict_type": "Debe ser un objeto.",
    "list_type": "Debe ser una lista.",
    "model_attributes_type": "Debe ser un objeto.",
    "json_invalid": "El cuerpo de la solicitud no es JSON válido.",
}
FALLBACK = "Valor no válido."
EMPTY = "No puede estar vacío."


def translate(error: dict[str, Any]) -> dict[str, Any]:
    """Rewrite one validation error in Spanish, keeping the shape the clients already read."""
    context = {
        name: f"{value:g}" if isinstance(value, float) else value
        for name, value in (error.get("ctx") or {}).items()
    }
    kind = error.get("type", "")

    if kind == "value_error" and "error" in context:
        message = str(context["error"])
    elif kind == "string_too_short" and context.get("min_length") == 1:
        message = EMPTY
    else:
        try:
            message = MESSAGES.get(kind, FALLBACK).format(**context)
        except (KeyError, IndexError):
            message = FALLBACK

    return {"type": kind, "loc": list(error.get("loc", ())), "msg": message}
