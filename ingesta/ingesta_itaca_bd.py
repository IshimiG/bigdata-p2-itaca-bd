"""Ingesta de ITACA desde la réplica PostgreSQL a la zona raw (JSON).

Es un volcado: cada tabla se lee con SELECT * y se guarda tal cual en
data/raw/<tabla>_<fecha>.json. La única transformación es el hash del NIA (HMAC-SHA256 con
sal secreta) en alumnos.nia y calificaciones.alumno. Las credenciales salen de .env.
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from datetime import date
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

RAIZ = Path(__file__).resolve().parents[1]
# .env antes de crear el logger: así LOG_LEVEL se tiene en cuenta
load_dotenv(RAIZ / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from logger import crear_logger  # noqa: E402

logger = crear_logger("ingesta_itaca_bd")

DIR_RAW = RAIZ / "data" / "raw"
FICHERO_SAL = RAIZ / "data" / ".sal_nia"
TABLAS = ["alumnos", "cursos", "calificaciones", "contenidos", "grupos"]
# columna con el NIA en cada tabla (se sustituye por su hash)
COLUMNA_NIA = {"alumnos": "nia", "calificaciones": "alumno"}

_cache_nia: dict[str, str] = {}
_sal = None


def conectar():
    """Abre la conexión con las credenciales de .env (la contraseña no se registra)."""
    try:
        parametros = {
            "host": os.environ["DB_HOST"],
            "port": os.environ["DB_PORT"],
            "dbname": os.environ["DB_NAME"],
            "user": os.environ["DB_USER"],
            "password": os.environ["DB_PASSWORD"],
        }
    except KeyError as e:
        raise RuntimeError(f"Falta la variable {e} en .env (copia .env.example a .env)") from e
    conexion = psycopg2.connect(connect_timeout=10, **parametros)
    conexion.set_session(readonly=True)
    logger.info("Conectado a %s:%s/%s como %s", parametros["host"], parametros["port"],
                parametros["dbname"], parametros["user"])
    return conexion


def extraer_tabla(conexion, tabla: str) -> list[dict]:
    """SELECT * de la tabla -> lista de dicts, tal cual está en la base."""
    inicio = time.perf_counter()
    with conexion.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(tabla)))
        filas = [dict(fila) for fila in cur.fetchall()]
    logger.info("%s: %d filas leídas en %.2f s", tabla, len(filas), time.perf_counter() - inicio)
    return filas


def _cargar_sal() -> bytes:
    """Sal secreta y estable (data/.sal_nia, permisos 600, fuera de Git)."""
    global _sal
    if _sal is None:
        if FICHERO_SAL.exists():
            _sal = FICHERO_SAL.read_bytes()
        else:
            _sal = secrets.token_hex(16).encode()
            FICHERO_SAL.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(FICHERO_SAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(_sal)
            logger.info("Sal nueva creada en %s (fuera de Git)", FICHERO_SAL)
    return _sal


def anonimizar_nia(nia) -> str:
    """HMAC-SHA256 del NIA con sal secreta, 10 hex. Con caché: mismo NIA, mismo hash."""
    nia = str(nia)
    if nia not in _cache_nia:
        _cache_nia[nia] = hmac.new(_cargar_sal(), nia.encode(), hashlib.sha256).hexdigest()[:10]
    return _cache_nia[nia]


def anonimizar_tabla(tabla: str, filas: list[dict]) -> None:
    """Sustituye el NIA por su hash; ordena por el hash para no dejar el orden del NIA."""
    columna = COLUMNA_NIA.get(tabla)
    if columna is None:
        return
    for fila in filas:
        fila[columna] = anonimizar_nia(fila[columna])
    filas.sort(key=lambda fila: fila[columna])


def guardar(datos: list[dict], nombre: str) -> Path:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    ruta = DIR_RAW / f"{nombre}_{date.today().isoformat()}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Guardados %d registros en %s", len(datos), ruta)
    return ruta


def main() -> int:
    inicio = time.perf_counter()
    conexion = None
    try:
        conexion = conectar()
        for tabla in TABLAS:
            filas = extraer_tabla(conexion, tabla)
            anonimizar_tabla(tabla, filas)
            guardar(filas, tabla)
        logger.info("NIA distintos anonimizados: %d", len(_cache_nia))
    except Exception:
        logger.exception("La ingesta ha fallado")
        return 1
    finally:
        if conexion is not None:
            conexion.close()
            logger.info("Conexión cerrada")
    logger.info("Ingesta completada en %.2f s", time.perf_counter() - inicio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
