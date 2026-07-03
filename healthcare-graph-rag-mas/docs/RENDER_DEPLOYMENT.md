# Render Deployment

Render does not run `docker compose up` directly. This project uses a Render Blueprint in the repository root (`render.yaml`) to create equivalent Docker services:

- `healthcare-graph-rag-api` public web service
- `healthcare-graph-rag-postgres` private pgvector service
- `healthcare-graph-rag-neo4j` private Neo4j service
- `healthcare-graph-rag-ollama` private Ollama service
- `healthcare-graph-rag-phoenix` private Phoenix service
- `healthcare-graph-rag-qdrant` private Qdrant service for mem0

## Deploy

1. Push the repository to GitHub.
2. In Render, choose **New > Blueprint**.
3. Select the GitHub repository.
4. Render should detect `render.yaml` at the repository root.
5. Review the generated services and create the blueprint.
6. Wait for all private services to deploy, then open the API service URL.

## Verify

Replace `<api-url>` with the public Render URL for `healthcare-graph-rag-api`.

```bash
curl https://<api-url>/health
curl -X POST https://<api-url>/api/briefings \
  -H "Content-Type: application/json" \
  -d '{"condition":"diabetes","audience":"health system strategy team","include_companies":true,"include_trials":true}'
```

## Vercel

Set the Vercel frontend environment variable:

```bash
VITE_API_BASE_URL=https://<api-url>
```

Redeploy the Vercel project after changing this value because Vite injects `VITE_*` variables at build time.

## Notes

Ollama can be slow on CPU-only plans. Use the largest practical Render plan for `healthcare-graph-rag-ollama`, or move Ollama to a GPU-backed host and set `OLLAMA_HOST` / `OLLAMA_PORT` on the API service accordingly.
