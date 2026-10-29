#!/bin/bash
# Carga en PostgreSQL los 5 SQL del profesor (sql/origen/, descargados de la tarea de Aules)
# con el usuario PROPIETARIO (nunca el de lectura) y aplica después los permisos.
# Uso, desde la raíz del proyecto:  docker compose up -d && ./sql/cargar_origen.sh
set -euo pipefail
cd "$(dirname "$0")/.."
CONTENEDOR=bigdata-pg-itaca
TABLAS=(cursos grupos alumnos contenidos calificaciones)

for t in "${TABLAS[@]}"; do
  [ -f "sql/origen/$t.sql" ] || { echo "Falta sql/origen/$t.sql (descárgalo de Aules, ver README)" >&2; exit 1; }
done

echo "Esperando a que PostgreSQL esté listo..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$CONTENEDOR" 2>/dev/null)" = healthy ]; do sleep 2; done

# POSTGRES_USER, POSTGRES_DB y DB_PASSWORD ya existen dentro del contenedor (los pasa el compose)
psqlc() { docker exec -i "$CONTENEDOR" bash -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"' _ "$@"; }

for t in "${TABLAS[@]}"; do
  echo "Cargando $t..."
  psqlc -f "/sql/origen/$t.sql"
done
echo "Aplicando permisos de solo lectura..."
psqlc -f /sql/02_permisos.sql
docker exec "$CONTENEDOR" bash /sql/03_password_lectura.sh
echo "Hecho. Filas por tabla:"
for t in "${TABLAS[@]}"; do
  printf '%-15s' "$t"; psqlc -t -A -c "SELECT count(*) FROM $t"
done
