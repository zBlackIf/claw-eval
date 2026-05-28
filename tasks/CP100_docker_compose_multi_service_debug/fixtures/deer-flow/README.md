# Deer Flow

AI-powered research and analysis workflow engine.

## Quick Start (Local)

```bash
conda activate deer
pip install -r requirements.txt
python -m deer_flow.api
```

## Docker Deployment

```bash
docker compose up -d
```

### Known Issues
- Provisioner requires DEER_FLOW_ROOT environment variable
- Kubeconfig volume mount: must be a file, not a directory
- Nginx proxy_pass must use Docker service names, not host IPs
- When using Docker, conda is not available - use pip in Dockerfile
