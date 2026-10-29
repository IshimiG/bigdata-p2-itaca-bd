#!/usr/bin/env bash
# Carga incremental de data/seed/*.sql en PostgreSQL.
#
# Antes de cargar, une los ficheros por curso de data/anual/ (<entidad>_AAAA_AA.sql)
# en una sola tabla por entidad (alumnos, calificaciones, contenidos, cursos, grupos),
# con la columna anyo que ya trae cada fichero. Genera data/seed/<entidad>.sql.
#
# Cada fichero cargado queda anotado en la tabla _registro_cargas (nombre, sha256,
# filas y fecha). En cada ejecución:
#   - fichero nuevo            -> se carga en una transacción y se registra
#   - fichero ya registrado    -> se salta (su sha256 no ha cambiado)
#   - fichero registrado con otro sha256 -> se detiene: no se recarga ni se borra nada
# Los DROP TABLE de los ficheros se quitan; las tablas se crean sólo si no existen.
# Uso: ./scripts/cargar_datos.sh [directorio_con_sql]   (por defecto data/seed)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
SEED_DIR="${1:-data/seed}"

psql_sql() {  # psql_sql <consulta> : devuelve el resultado sin cabeceras
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -c "$1"
}
psql_stdin() {  # psql_stdin : ejecuta SQL recibido por stdin
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q
}

psql_sql "CREATE TABLE IF NOT EXISTS _registro_cargas (
  fichero text PRIMARY KEY,
  sha256 text NOT NULL,
  filas integer NOT NULL,
  cargado_en timestamptz NOT NULL DEFAULT now()
);" >/dev/null

# Une data/anual/<entidad>_*.sql en $SEED_DIR/<entidad>.sql: un CREATE TABLE (el del
# primer curso) seguido de los INSERT de todos los cursos, en orden. Es determinista:
# mismos ficheros de origen, mismo sha256.
unir_anual() {
  local entidad f out total create
  for entidad in alumnos calificaciones contenidos cursos grupos; do
    local origenes=("data/anual/${entidad}"_*.sql)
    [ -e "${origenes[0]}" ] || continue
    out="$SEED_DIR/$entidad.sql"
    total=0
    for f in "${origenes[@]}"; do
      total=$((total + $(grep -oE '· [0-9]+ filas' "$f" | grep -oE '[0-9]+')))
    done
    {
      echo "-- Consolidado de ${#origenes[@]} cursos (data/anual/${entidad}_*.sql) · $total filas"
      echo
      awk '/^CREATE TABLE/{c=1} c&&/^\);/{c=0; exit} c' "${origenes[0]}" \
        | sed -E "s/^CREATE TABLE ${entidad}_[0-9_]+ /CREATE TABLE ${entidad} /"
      echo ");"
      for f in "${origenes[@]}"; do
        awk '/^CREATE TABLE/{c=1} c&&/^\);/{c=0; b=1; next} b' "$f" \
          | sed -E "s/^INSERT INTO ${entidad}_[0-9_]+ /INSERT INTO ${entidad} /"
      done
    } > "$out.tmp"
    mv "$out.tmp" "$out"
    echo "UNIDO    $entidad.sql ($total filas, ${#origenes[@]} cursos)"
  done
}
unir_anual

for f in "$SEED_DIR"/*.sql; do
  nombre=$(basename "$f")
  tabla=${nombre%.sql}
  sha=$(sha256sum "$f" | cut -d' ' -f1)
  esperadas=$(grep -oE '· [0-9]+ filas' "$f" | grep -oE '[0-9]+')
  registrado=$(psql_sql "SELECT sha256 FROM _registro_cargas WHERE fichero='$nombre';")

  if [ -n "$registrado" ]; then
    if [ "$registrado" = "$sha" ]; then
      echo "SALTADO  $nombre (ya cargado)"; continue
    fi
    echo "ERROR    $nombre ha cambiado desde su carga. No lo recargo ni borro nada." >&2
    exit 1
  fi

  if [ "$(psql_sql "SELECT to_regclass('public.$tabla') IS NOT NULL;")" = "t" ]; then
    # Tabla creada en una carga anterior sin registro: se comprueba y se registra
    actuales=$(psql_sql "SELECT count(*) FROM $tabla;")
    if [ "$actuales" != "$esperadas" ]; then
      echo "ERROR    $tabla tiene $actuales filas y se esperaban $esperadas. No la toco." >&2
      exit 1
    fi
    psql_sql "INSERT INTO _registro_cargas (fichero, sha256, filas) VALUES ('$nombre', '$sha', $actuales);" >/dev/null
    echo "REGISTRADO $nombre (tabla existente, $actuales filas)"
    continue
  fi

  {
    echo "BEGIN;"
    sed -e '/^DROP TABLE IF EXISTS/d' \
        -e 's/^CREATE TABLE /CREATE TABLE IF NOT EXISTS /' "$f"
    actuales_sql="SELECT count(*) FROM $tabla"
    echo "INSERT INTO _registro_cargas (fichero, sha256, filas) VALUES ('$nombre', '$sha', (SELECT count(*) FROM $tabla));"
    echo "COMMIT;"
  } | psql_stdin
  filas=$(psql_sql "SELECT count(*) FROM $tabla;")
  if [ "$filas" != "$esperadas" ]; then
    echo "ERROR    $nombre: $filas filas cargadas, se esperaban $esperadas" >&2
    exit 1
  fi
  echo "CARGADO  $nombre ($filas filas)"
done
