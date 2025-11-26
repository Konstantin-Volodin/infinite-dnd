# Hybrid MCP Starter (Python / FastAPI)

This starter implements a hybrid design:
- Canonical game lore & rules: read-only JSON files in `world-setup/` (git-managed)
- Mutable runtime state: stored in Postgres (`world-state/` seeded on first run)
- MCP-like endpoints served by FastAPI (`main.py`)

Quickstart:
1. Start Postgres:
   docker-compose up -d
2. Create a virtualenv and install:
   pip install -r requirements.txt
3. Start the server:
   python main.py
4. Explore Swagger UI:
   http://localhost:8000/docs

Notes:
- Canonical files are read-only. Mutable state updates go to Postgres.
- The mutation endpoint requires an API key header `x-api-key` (default: `dev-secret`) — change for production.