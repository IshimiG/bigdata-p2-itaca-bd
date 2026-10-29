#!/bin/bash
# Pone la contraseña del usuario de lectura desde la variable DB_PASSWORD (definida en .env),
# para no escribirla nunca en un fichero versionado.
set -e
psql -v ON_ERROR_STOP=1 -v pw="$DB_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
ALTER ROLE lectura_bigdata PASSWORD :'pw';
SQL
