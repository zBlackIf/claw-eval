"""Configuration template - agent should expand this."""
# Chunking parameters
CHUNK_SIZE = 500
OVERLAP_SIZE = 50

# Storage
MINIO_ENDPOINT = "localhost:9000"
MINIO_BUCKET = "documents"
ES_INDEX = "document_chunks"
PG_DSN = "postgresql://user:pass@localhost:5432/ragdb"
