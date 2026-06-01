---
name: 04-rsdd-architecture
description: Generate RSDD Chapter 4 (Architecture). Describe system architecture, applicable systems, and involved components.
---

# RSDD Chapter 4: Architecture

## Task

Based on the requirement and preceding chapters, generate architecture chapter:
- 4.1 System Architecture — high-level architecture description
- 4.2 Applicable Systems — which products/systems are affected
- 4.3 Involved Components — specific modules and their roles

## Rules

1. Architecture section must describe component relationships
2. List ALL affected systems mentioned in the requirement
3. For each component, specify: name, role, change scope
4. Include an ASCII architecture diagram if possible
5. Structure must follow template-chapter.md

## Input

- `workspace/<REQ-ID>/voc.md` — source requirement
- `workspace/<REQ-ID>/rsdd.md` — existing RSDD with Chapters 1-3

## Output

- Append Chapter 4 to `workspace/<REQ-ID>/rsdd.md`
