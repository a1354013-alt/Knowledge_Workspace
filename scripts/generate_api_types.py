from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "docs" / "openapi.json"
OUT_PATH = ROOT / "frontend" / "src" / "api" / "generated" / "api-types.ts"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def schema_to_ts(name: str, schema: dict) -> str:
    if schema.get("type") == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines = [f"export interface {name} {{"]
        for key, prop in sorted(props.items()):
            optional = "" if key in required else "?"
            lines.append(f"  {key}{optional}: {type_to_ts(prop)};")
        lines.append("}")
        return "\n".join(lines)
    return f"export type {name} = {type_to_ts(schema)};"


def object_to_ts(schema: dict) -> str:
    props = schema.get("properties", {})
    if not props:
        return "Record<string, unknown>"
    required = set(schema.get("required", []))
    entries: list[str] = []
    for key, prop in sorted(props.items()):
        optional = "" if key in required else "?"
        entries.append(f"{key}{optional}: {type_to_ts(prop)}")
    return "{ " + "; ".join(entries) + " }"


def type_to_ts(schema: dict) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "const" in schema:
        return json.dumps(schema["const"])
    if "anyOf" in schema:
        return " | ".join(
            _dedupe_preserve_order([type_to_ts(item) for item in schema["anyOf"]])
        )
    if "enum" in schema:
        return " | ".join(
            _dedupe_preserve_order([json.dumps(value) for value in schema["enum"]])
        )
    kind = schema.get("type")
    if kind == "array":
        return f"{type_to_ts(schema.get('items', {}))}[]"
    if kind == "integer" or kind == "number":
        return "number"
    if kind == "boolean":
        return "boolean"
    if kind == "object":
        return object_to_ts(schema)
    if kind == "null":
        return "null"
    return "string" if kind == "string" else "unknown"


def generate() -> str:
    if not OPENAPI_PATH.exists():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "export_openapi.py")], check=True
        )
    data = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    schemas = data.get("components", {}).get("schemas", {})
    body = [
        "/* Generated from docs/openapi.json. Do not edit by hand. */",
        "/* Run: npm run generate:api-types */",
        "",
    ]
    for name, schema in sorted(schemas.items()):
        body.append(schema_to_ts(name, schema))
        body.append("")
    return "\n".join(body).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate lightweight TypeScript types from OpenAPI schemas."
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = generate()
    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8") != content:
            raise SystemExit(
                "Generated API types are out of date. Run npm run generate:api-types."
            )
        print("OK: generated API types are up to date")
        return 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
