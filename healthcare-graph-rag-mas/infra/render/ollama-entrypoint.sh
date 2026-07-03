#!/bin/sh
set -eu

ollama serve &
ollama_pid="$!"

until ollama list >/dev/null 2>&1; do
  sleep 2
done

ollama pull "${OLLAMA_MODEL:-llama3.2}" || true

wait "$ollama_pid"
