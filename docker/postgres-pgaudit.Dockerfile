# Stage 25 (G-060) — pgvector + pgaudit Postgres image.
#
# The live container was enabled in-place (apt install + ALTER SYSTEM shared_preload_libraries='pgaudit' +
# pgaudit.log='write, ddl, role' + pgaudit.log_parameter=on — settings persist in postgresql.auto.conf inside the
# data volume). This Dockerfile makes the PACKAGE durable across container recreation: rebuild with
#
#   docker build -f docker/postgres-pgaudit.Dockerfile -t ai-agent-postgres-pgaudit:pg15 docker/
#
# and point docker-compose.yml `image:` here when recreating. pgaudit provides the DB-LEVEL session audit trail
# (defence-in-depth: catches direct-SQL access that bypasses the app); the app-level signed append-only audit_chain
# (migration 0003) remains the EU-AI-Act Art-12 evidence. Policy per research §36.3 (conservative: write/ddl/role).
FROM pgvector/pgvector:pg15
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends postgresql-15-pgaudit \
    && rm -rf /var/lib/apt/lists/*
