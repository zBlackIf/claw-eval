# Alarm Scan Engine - Design Specification

## Overview
The alarm-scan-engine scans infrastructure metrics and classifies alerts
into severity categories using configurable rules.

## Architecture
1. Scanner Layer: Periodically polls metrics from data sources
2. Rule Engine: Evaluates conditions and thresholds
3. Classifier: Maps matched rules to alarm severity (CRITICAL/WARNING/INFO)
4. Notifier: Dispatches alerts to configured channels (email, webhook, SMS)
5. Storage: Persists alarm history for audit

## Required Components
- AlarmScanner interface with scan() method
- RuleEngine with addRule(), evaluate() methods
- AlarmClassifier with classify(metric, rules) -> AlarmLevel
- NotificationDispatcher supporting multiple channels
- AlarmRepository for CRUD operations on alarm records
- Configuration via YAML files

## Design Patterns Required
- Strategy pattern for notification channels
- Chain of responsibility for rule evaluation
- Repository pattern for data access
- Builder pattern for Alarm objects
