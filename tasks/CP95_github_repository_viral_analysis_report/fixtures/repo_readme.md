# Andrej Karpathy's Claude Code Skills

This repository contains Andrej Karpathy's Claude Code configuration, skills, and agent definitions, extracted from his public live coding streams.

## What's Inside

- **CLAUDE.md** - Main configuration file that defines coding standards, agent orchestration rules, and project preferences
- **.claude/rules/** - Modular rule files for coding style, testing, git workflow, security
- **skills/** - Specialized skill definitions for deep research, code review, TDD
- **agents/** - Agent persona definitions for planner, architect, code-reviewer roles

## How to Use

1. Clone this repo
2. Copy the relevant files to your own `~/.claude/` directory
3. Customize the rules and skills to match your workflow

## Key Concepts

### CLAUDE.md
The main instruction file that Claude Code reads at the start of every session. Karpathy's version emphasizes:
- Agent-first design: delegate to specialized agents
- Test-driven development: write tests before code
- Immutability: never mutate objects or arrays
- Many small files over few large files

### Skills
Reusable workflows that agents can invoke:
- **deep-research**: Multi-angle research before answering
- **code-review**: Comprehensive code review checklist
- **tdd-guide**: Red-green-refactor workflow

### Agents
Specialized personas for different tasks:
- **planner**: Creates implementation plans
- **architect**: Makes design decisions
- **code-reviewer**: Reviews code quality and security

## Disclaimer

This is a community project. The configurations were extracted from public streams and may not represent Karpathy's current or complete setup. Use at your own discretion.

## License

MIT
