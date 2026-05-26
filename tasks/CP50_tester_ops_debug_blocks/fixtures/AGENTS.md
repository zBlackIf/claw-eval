# AI Tester Ops - Agent Guide

## Architecture
Three-level file structure, ALL MUST EXIST before proceeding:
1. `memory/user_preferences.md` - User preferences and identification
2. `workspace/TODO.md` - All test projects master list
3. `workspace/<project>/todolist.md` - Individual project progress

## Testing Workflow Phases
| Phase | Description | Quality Check |
|-------|------------|---------------|
| 0 | Create project structure | Directory and templates exist |
| 1 | Requirements analysis | Clarification table + test scope defined |
| 2 | Impact analysis | Direct/indirect impact separated |
| 3 | Test plan | 5W1H complete |
| 4 | Test case design | Every requirement covered |
| 5 | Test execution | Results stats complete |
| 6 | Defect reporting | 9 elements complete per defect |
| 7 | Test summary | Quality assessment + go/no-go conclusion |

## Rules
1. Check all 3 prerequisite files before ANY work
2. If any file missing, BLOCK and prompt user
3. Each phase must pass quality check before next
4. Never skip phases
