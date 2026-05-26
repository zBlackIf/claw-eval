# Project Architecture Overview

## Backend Services

The backend consists of three microservices:

### API Gateway
Handles authentication and request routing.
All external requests pass through this service.

### Document Service
Processes uploaded documents and extracts text.

#### Supported Formats
- PDF (electronic and scanned)
- DOCX
- TXT and Markdown

### Search Service
Provides full-text search via Elasticsearch.

## Database Schema

Documents are stored with parent-child relationships
to support hierarchical chunking.
