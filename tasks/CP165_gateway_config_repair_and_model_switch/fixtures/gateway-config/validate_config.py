#!/usr/bin/env python3
"""Gateway config validator - mimics the strict JSON schema validation."""
import json
import sys
from pathlib import Path


def validate_config(config_path: Path, schema_path: Path) -> list[str]:
    """Validate config against schema. Returns list of error messages."""
    errors = []

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"Cannot load schema: {e}"]

    def check_additional_properties(obj, schema_node, path="<root>"):
        """Recursively check for additionalProperties violations."""
        if not isinstance(obj, dict) or not isinstance(schema_node, dict):
            return

        if schema_node.get("additionalProperties") is False:
            allowed = set(schema_node.get("properties", {}).keys())
            for key in obj:
                if key not in allowed:
                    errors.append(f'{path}: Unrecognized key: "{key}"')

        props = schema_node.get("properties", {})
        for key, val in obj.items():
            if key in props and isinstance(val, dict):
                prop_schema = props[key]
                if prop_schema.get("type") == "object":
                    if "additionalProperties" in prop_schema and isinstance(prop_schema["additionalProperties"], dict):
                        # Pattern properties (like channels/plugins) - check each value
                        for sub_key, sub_val in val.items():
                            if isinstance(sub_val, dict):
                                check_additional_properties(sub_val, prop_schema["additionalProperties"], f"{path}.{key}.{sub_key}")
                    else:
                        check_additional_properties(val, prop_schema, f"{path}.{key}")

    def check_enum(obj, schema_node, path="<root>"):
        """Recursively check enum constraints."""
        if not isinstance(obj, dict) or not isinstance(schema_node, dict):
            return
        props = schema_node.get("properties", {})
        for key, val in obj.items():
            if key in props:
                prop_schema = props[key]
                if "enum" in prop_schema and val not in prop_schema["enum"]:
                    errors.append(f'{path}.{key}: Value "{val}" not in allowed values: {prop_schema["enum"]}')
                elif isinstance(val, dict) and prop_schema.get("type") == "object":
                    if "additionalProperties" in prop_schema and isinstance(prop_schema["additionalProperties"], dict):
                        for sub_key, sub_val in val.items():
                            if isinstance(sub_val, dict):
                                check_enum(sub_val, prop_schema["additionalProperties"], f"{path}.{key}.{sub_key}")
                    else:
                        check_enum(val, prop_schema, f"{path}.{key}")

    def check_required(obj, schema_node, path="<root>"):
        """Recursively check required fields."""
        if not isinstance(obj, dict) or not isinstance(schema_node, dict):
            return
        required = schema_node.get("required", [])
        for field in required:
            if field not in obj:
                errors.append(f'{path}: Missing required field: "{field}"')

        props = schema_node.get("properties", {})
        for key, val in obj.items():
            if key in props and isinstance(val, dict):
                prop_schema = props[key]
                if prop_schema.get("type") == "object":
                    if "additionalProperties" in prop_schema and isinstance(prop_schema["additionalProperties"], dict):
                        for sub_key, sub_val in val.items():
                            if isinstance(sub_val, dict):
                                check_required(sub_val, prop_schema["additionalProperties"], f"{path}.{key}.{sub_key}")
                    else:
                        check_required(val, prop_schema, f"{path}.{key}")

    check_additional_properties(config, schema)
    check_enum(config, schema)
    check_required(config, schema)

    return errors


def main():
    config_dir = Path("/workspace/fixtures/gateway-config")
    if not config_dir.exists():
        config_dir = Path("/workspace/gateway-config")

    config_path = config_dir / "gateway.json"
    schema_path = config_dir / "schema.json"

    if not config_path.exists():
        print("ERROR: gateway.json not found")
        sys.exit(1)
    if not schema_path.exists():
        print("ERROR: schema.json not found")
        sys.exit(1)

    errors = validate_config(config_path, schema_path)
    if errors:
        print("Config invalid")
        print(f"File: {config_path}")
        print("Problems:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Config valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
