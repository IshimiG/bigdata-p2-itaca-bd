#!/usr/bin/env bash
# Carga los ficheros de data/seed/*.sql en PostgreSQL.
# No borra nada: quita los DROP TABLE de los ficheros, crea las tablas sólo si
# no existen y, si una tabla ya tiene las filas esperadas, la salta.
# Si una tabla existe con otro número de filas, se detiene sin tocarla.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

psql_in() {  # psql_in <sql-stdin> : ejecuta contra el contenedor
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At "$@"
}

for f in data/seed/*.sql; do
  tabla=$(basename "$f" .sql)
  esperadas=$(grep -oE '· [0-9]+ filas' "$f" | grep -oE '[0-9]+')
  existe=$(echo "SELECT to_regclass('public.$tabla') IS NOT NULL;" | psql_in)
  if [ "$existe" = "t" ]; then
    actuales=$(echo "SELECT count(*) FROM $tabla;" | psql_in)
    if [ "$actuales" = "$esperadas" ]; then
      echo "OK      $tabla ($actuales filas, ya cargada)"; continue
    fi
    echo "ERROR   $tabla tiene $actuales filas y se esperaban $esperadas. No la toco." >&2
    exit 1
  fi
  sed -e '/^DROP TABLE IF EXISTS/d' \
      -e 's/^CREATE TABLE /CREATE TABLE IF NOT EXISTS /' "$f" \
    | (echo "BEGIN;"; cat; echo "COMMIT;") \
    | psql_in >/dev/null
  actuales=$(echo "SELECT count(*) FROM $tabla;" | psql_in)
  echo "CARGADA $tabla ($actuales filas)"
done
