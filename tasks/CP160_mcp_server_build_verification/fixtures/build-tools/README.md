# Build Verification Tools

This directory contains CLI tools for the build migration verification pipeline:

## Tools

### `build_project.py`
Generates build artifacts from `build_defs/` JSON definitions.

```bash
python build_project.py <project_dir> [config]
# config: Release (default) or Debug
```

Returns JSON: `{success, artifacts, errors}`

### `reference_build.py`
Generates reference artifacts from `legacy_defs/` JSON definitions (legacy toolchain).

```bash
python reference_build.py <project_dir> [config]
```

Returns JSON: `{success, artifacts, errors}`

### `compare_artifacts.py`
Compares build_output vs reference_output artifacts for consistency.

```bash
python compare_artifacts.py <project_dir> [--module name] [--config Release|Debug]
```

Returns JSON: `{match, total, matched, mismatched, details}`

### `detect_changes.py`
Detects which build definition files have been modified recently.

```bash
python detect_changes.py <project_dir> [--since N]
```

Returns JSON: `{changed_files, build_defs_changed, legacy_defs_changed}`

## Pipeline

The typical verification workflow is:
1. `detect_changes.py` - find what changed
2. `build_project.py` - generate new artifacts
3. `reference_build.py` - generate reference artifacts
4. `compare_artifacts.py` - compare for consistency

## MCP Server Requirement

We need an MCP server (`server.py`) that exposes these 4 tools + a `full_verify` composite tool via the stdio transport protocol. The server should use the `mcp` Python package (see `requirements.txt`).

Each CLI tool should be wrapped as an MCP tool with appropriate parameters and return the JSON results directly.
