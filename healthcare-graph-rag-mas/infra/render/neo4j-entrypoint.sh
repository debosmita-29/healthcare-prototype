#!/bin/bash
set -euo pipefail

export NEO4J_AUTH="${NEO4J_USERNAME:-neo4j}/${NEO4J_PASSWORD:?NEO4J_PASSWORD is required}"

exec /startup/docker-entrypoint.sh "$@"
