#!/usr/bin/env bash
# Levanta PostgreSQL, espera a que esté sano y carga los datos de Aules.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d
until [ "$(docker inspect -f '{{.State.Health.Status}}' bigdata-postgres 2>/dev/null)" = "healthy" ]; do sleep 2; done
./scripts/cargar_datos.sh
