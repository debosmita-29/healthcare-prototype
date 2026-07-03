FROM ollama/ollama:latest

COPY infra/render/ollama-entrypoint.sh /ollama-entrypoint.sh
RUN chmod +x /ollama-entrypoint.sh

ENTRYPOINT ["/bin/sh", "/ollama-entrypoint.sh"]
