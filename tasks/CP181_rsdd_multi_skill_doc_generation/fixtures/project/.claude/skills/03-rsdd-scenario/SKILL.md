---
name: 03-rsdd-scenario
description: Generate RSDD Chapter 3 (Scenarios). Create scenario inventory, value assessment, and complexity evaluation.
---

# RSDD Chapter 3: Scenarios

## Task

Based on the requirement, generate scenario analysis including:
- 3.1 Scenario Inventory — enumerate all functional scenarios
- 3.2 Value Assessment — rate business value of each scenario
- 3.3 Complexity Evaluation — assess implementation complexity
- 3.4 Similar Requirement Analysis — reference existing implementations

## Rules

1. Each scenario must have: ID, name, description, priority
2. Value assessment uses H/M/L scale with justification
3. Complexity uses H/M/L with technical rationale
4. Similar requirements must reference actual system modules if applicable
5. Structure must follow template-chapter.md

## Input

- `workspace/<REQ-ID>/voc.md` — source requirement
- `workspace/<REQ-ID>/rsdd.md` — existing RSDD with Chapters 1-2

## Output

- Append Chapter 3 to `workspace/<REQ-ID>/rsdd.md`
