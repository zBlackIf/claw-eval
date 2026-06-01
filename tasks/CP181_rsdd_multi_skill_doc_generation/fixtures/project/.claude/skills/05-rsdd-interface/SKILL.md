---
name: 05-rsdd-interface
description: Generate RSDD Chapter 5 (Interfaces). Define interface protocol and list all interfaces with details.
---

# RSDD Chapter 5: Interfaces

## Task

Based on the requirement and architecture, generate interface chapter:
- 5.1 Interface Protocol — specify API style, auth, format
- 5.2 Interface List — enumerate all interfaces with details

## Rules

1. Interface protocol must specify: style (REST/gRPC/SOAP), auth method, data format
2. Each interface must have: ID, name, method, path, description, request/response summary
3. Interfaces must cover ALL functionality mentioned in scenarios (Chapter 3)
4. Group interfaces by functional module
5. Structure must follow template-chapter.md

## Input

- `workspace/<REQ-ID>/voc.md` — source requirement
- `workspace/<REQ-ID>/rsdd.md` — existing RSDD with Chapters 1-4

## Output

- Append Chapter 5 to `workspace/<REQ-ID>/rsdd.md`
