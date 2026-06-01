---
name: 02-rsdd-environment
description: Generate RSDD Chapter 2 (Environment). Based on voc.md and Chapter 1 content, produce 2.1 Network Topology and 2.2 Key Environment Factors.
---

# RSDD Chapter 2: Environment

## Task

Based on the requirement document and RSDD Chapter 1, generate the environment chapter describing:
- 2.1 Network Topology — describe how the system fits into the network
- 2.2 Key Environment Factors — list critical environment constraints

## Rules

1. Reference voc.md for deployment context (product form, platform)
2. Identify all systems/components mentioned in the requirement
3. Describe the topology relationships between components
4. List environment factors: OS, middleware, dependencies, protocols
5. Structure must follow template-chapter.md

## Input

- `workspace/<REQ-ID>/voc.md` — source requirement
- `workspace/<REQ-ID>/rsdd.md` — existing RSDD with Chapter 1

## Output

- Append Chapter 2 to `workspace/<REQ-ID>/rsdd.md`
