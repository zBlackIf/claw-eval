# Strategy Module Requirements (Module 3)

## Overview
The strategy module manages 20+ trading strategies with version control and performance tracking.

## Core Requirements

### 1. Strategy Display
- Show all available strategies in a list/table
- Each strategy displays: name, current version number, current weight, recent win rate
- No direct "add strategy" button on this page (strategies are created only through backtesting)

### 2. Strategy Version Management
- Each strategy can have multiple versions
- Users can create new version numbers for existing strategies
- Each version configures which factors to activate and their weights
- Version format: v{major}.{minor} (e.g., v1.0, v1.1, v2.0)

### 3. Version Publishing Rules
- New versions start in "draft" status
- Versions must pass backtesting validation before publishing
- Only published versions can be used in the live strategy engine
- Maximum one active (published) version per strategy

### 4. Data Fields Per Strategy
| Field | Description |
|-------|-------------|
| Strategy Name | Display name of the strategy |
| Current Version | Active version number |
| Weight | Current allocation weight (0.0-1.0) |
| Win Rate | Recent win rate percentage |
| Status | Active/Paused/Disabled |
| Last Updated | Timestamp of last modification |

### 5. Constraints
- Users CANNOT add new strategies from the strategy management page
- New strategies can ONLY be created through the backtesting module (Module 8)
- Users CAN add new versions to existing strategies
- Version publishing requires backtesting validation pass
