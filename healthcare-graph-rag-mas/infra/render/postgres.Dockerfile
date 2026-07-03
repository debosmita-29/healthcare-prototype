FROM pgvector/pgvector:pg16

COPY infra/postgres/init.sql /docker-entrypoint-initdb.d/init.sql
