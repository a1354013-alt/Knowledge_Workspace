from __future__ import annotations

from importlib import import_module


def test_type_to_ts_handles_nullable_enum_const_and_refs():
    generator = import_module("scripts.generate_api_types")

    schema = {
        "anyOf": [
            {"$ref": "#/components/schemas/Example"},
            {"type": "null"},
            {"enum": ["queued", "failed"]},
            {"const": "fixed"},
        ]
    }

    assert generator.type_to_ts(schema) == 'Example | null | "queued" | "failed" | "fixed"'


def test_type_to_ts_handles_nested_object_and_array_items():
    generator = import_module("scripts.generate_api_types")

    schema = {
        "type": "object",
        "required": ["items", "meta"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                },
            },
            "meta": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "detail": {"$ref": "#/components/schemas/MetaDetail"},
                },
            },
        },
    }

    assert (
        generator.type_to_ts(schema)
        == "{ items: { count?: number; id: string }[]; meta: { detail?: MetaDetail; ok?: boolean } }"
    )
