# Hosted Docker Stack

This stack runs the production-like prototype on one Docker host.

## Internal service URLs

Use these values inside Docker Compose:

```bash
DATABASE_URL=postgresql://health:<password>@postgres:5432/healthrag
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006
MEM0_ENABLED=true
MEM0_VECTOR_STORE_PROVIDER=qdrant
MEM0_QDRANT_HOST=qdrant
MEM0_QDRANT_PORT=6333
NEMO_GUARDRAILS_CONFIG=/app/guardrails
```

The public Vercel frontend should only point at the API URL:

```bash
VITE_API_BASE_URL=https://<your-api-domain>
```

## Run

```bash
cp deploy/hosted.env.example deploy/hosted.env
docker compose --env-file deploy/hosted.env -f docker-compose.hosted.yml up -d --build
```

Load the Ollama model once after the containers start:

```bash
docker compose --env-file deploy/hosted.env -f docker-compose.hosted.yml exec ollama ollama pull llama3.2
```

## Verify

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/briefings \
  -H "Content-Type: application/json" \
  -d '{"condition":"diabetes","audience":"health system strategy team","include_companies":true,"include_trials":true}'
```

Postgres, Neo4j, Ollama, Phoenix, and Qdrant bind to `127.0.0.1` by default for safer hosting. Use SSH tunnels for admin access, or put them behind a private network/VPN. The API port is the only port intended to be public.
