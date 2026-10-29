"""Ingesta de ITACA desde la réplica PostgreSQL a la zona raw (JSON).

Se conecta con psycopg2 (el equivalente Python de JDBC) con el usuario de solo lectura,
lee cada tabla, anonimiza el NIA (HMAC-SHA256 con sal secreta) y guarda
data/raw/<tabla>_<fecha>.json. Las credenciales salen de .env, nunca del código.
"""
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from datetime import date

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logger import crear_logger  # noqa: E402

logger = crear_logger("ingesta_itaca_bd")

DIR_RAW = "data/raw"
FICHERO_SAL = "data/.sal_nia"
TABLAS = ["alumnos", "cursos", "calificaciones", "contenidos", "grupos"]
CAMPOS_NIA = {"NIA", "alumno"}  # columnas con el NIA, que se anonimizan
COLUMNAS_TECNICAS = {"id"}      # claves artificiales de la réplica: no forman parte del dato


def conectar():
    """Abre la conexión con las credenciales de .env (la contraseña no se registra)."""
    load_dotenv()
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
    # el usuario es de solo lectura: lo reflejamos también en la sesión
    conexion.set_session(readonly=True)
    logger.info("Conectado a %s:%s/%s como %s", parametros["host"], parametros["port"],
                parametros["dbname"], parametros["user"])
    return conexion


def extraer_tabla(conexion, tabla: str) -> list[dict]:
    """SELECT * de la tabla (nombre como identificador, no concatenado) -> lista de dicts.

    El ORDER BY por las tres primeras columnas hace la salida determinista.
    """
    consulta = sql.SQL("SELECT * FROM {} ORDER BY 1, 2, 3").format(sql.Identifier(tabla))
    inicio = time.perf_counter()
    with conexion.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(consulta)
        filas = [{k: v for k, v in fila.items() if k not in COLUMNAS_TECNICAS} for fila in cur.fetchall()]
    logger.info("%s: %d filas leídas en %.2f s", tabla, len(filas), time.perf_counter() - inicio)
    return filas


def cargar_sal() -> bytes:
    """Sal secreta y estable: evita deshacer el hash probando todos los NIA."""
    if os.path.exists(FICHERO_SAL):
        with open(FICHERO_SAL, "rb") as f:
            return f.read()
    sal = secrets.token_hex(16).encode()
    os.makedirs(os.path.dirname(FICHERO_SAL), exist_ok=True)
    with open(FICHERO_SAL, "wb") as f:
        f.write(sal)
    logger.info("Sal nueva creada en %s (está fuera de Git)", FICHERO_SAL)
    return sal


class Anonimizador:
    """Un único hash por NIA original, reutilizado en alumnos y calificaciones."""

    def __init__(self, sal: bytes):
        self.sal = sal
        self.cache: dict[str, str] = {}

    def __call__(self, nia: str) -> str:
        if nia not in self.cache:
            self.cache[nia] = hmac.new(self.sal, nia.encode(), hashlib.sha256).hexdigest()[:10]
        return self.cache[nia]


def anonimizar_filas(filas: list[dict], anonimizar) -> None:
    """Sustituye in situ el NIA por su hash; el texto vacío pasa a null."""
    for fila in filas:
        for campo, valor in fila.items():
            if isinstance(valor, str):
                valor = valor.strip() or None
                fila[campo] = valor
            if campo in CAMPOS_NIA and valor:
                fila[campo] = anonimizar(valor)


def guardar(datos: list[dict], nombre: str) -> str:
    ruta = os.path.join(DIR_RAW, f"{nombre}_{date.today().isoformat()}.json")
    os.makedirs(DIR_RAW, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Guardados %d registros en %s", len(datos), ruta)
    return ruta


# Comprobaciones de integridad en SQL sobre la réplica (cuentan huérfanos).
# La clave incluye anyo y curso. Son consultas fijas, sin datos externos.
CONSULTAS_INTEGRIDAD = [
    ("calificaciones.contenido -> contenidos",
     "SELECT count(*) FROM calificaciones c LEFT JOIN contenidos m "
     "ON (m.anyo, m.curso, m.codigo) = (c.anyo, c.curso, c.contenido) WHERE m.codigo IS NULL"),
    ("alumnos.grupo -> grupos",
     "SELECT count(*) FROM alumnos a LEFT JOIN grupos g ON (g.anyo, g.codigo) = (a.anyo, a.grupo) "
     "WHERE a.grupo IS NOT NULL AND g.codigo IS NULL"),
    ("calificaciones.alumno -> alumnos",
     "SELECT count(*) FROM calificaciones c WHERE NOT EXISTS "
     "(SELECT 1 FROM alumnos a WHERE a.anyo = c.anyo AND a.\"NIA\" = c.alumno)"),
]


def validar_sql(conexion) -> dict[str, int]:
    """Huérfanos según la propia base de datos (con NIA original, antes de anonimizar)."""
    resultado = {}
    with conexion.cursor() as cur:
        for nombre, consulta in CONSULTAS_INTEGRIDAD:
            cur.execute(consulta)
            resultado[nombre] = cur.fetchone()[0]
    return resultado


def validar(datos: dict[str, list[dict]]) -> dict[str, int]:
    """Lo mismo sobre los datos ya anonimizados que se van a guardar."""
    modulos = {(r["anyo"], r["curso"], r["codigo"]) for r in datos["contenidos"]}
    grupos = {(r["anyo"], r["codigo"]) for r in datos["grupos"]}
    alumnos = {(r["anyo"], r["NIA"]) for r in datos["alumnos"]}
    return {
        "calificaciones.contenido -> contenidos":
            sum(1 for r in datos["calificaciones"] if (r["anyo"], r["curso"], r["contenido"]) not in modulos),
        "alumnos.grupo -> grupos":
            sum(1 for r in datos["alumnos"] if r["grupo"] and (r["anyo"], r["grupo"]) not in grupos),
        "calificaciones.alumno -> alumnos":
            sum(1 for r in datos["calificaciones"] if (r["anyo"], r["alumno"]) not in alumnos),
    }


def informar(origen: str, huerfanos: dict[str, int]) -> None:
    for nombre, n in huerfanos.items():
        # se informa pero no se descarta: el hueco está en el origen
        if n:
            logger.warning("[%s] %s: %d huérfanos", origen, nombre, n)
        else:
            logger.info("[%s] %s: correcto", origen, nombre)


def main() -> int:
    inicio = time.perf_counter()
    conexion = None
    try:
        conexion = conectar()
        anonimizar = Anonimizador(cargar_sal())
        datos: dict[str, list[dict]] = {}
        for tabla in TABLAS:
            datos[tabla] = extraer_tabla(conexion, tabla)
        informar("SQL", validar_sql(conexion))
        for tabla, filas in datos.items():
            anonimizar_filas(filas, anonimizar)
            guardar(filas, tabla)
        sin_grupo = sum(1 for r in datos["alumnos"] if not r["grupo"])
        logger.info("Alumnos sin grupo asignado en el origen: %d (no se consideran huérfanos)", sin_grupo)
        informar("JSON", validar(datos))
        logger.info("NIA distintos anonimizados: %d", len(anonimizar.cache))
    except psycopg2.OperationalError:
        logger.exception("No se puede conectar con la base de datos (¿contenedor parado, puerto o credenciales?)")
        return 1
    except psycopg2.Error:
        logger.exception("Error de PostgreSQL durante la extracción")
        return 1
    except (RuntimeError, OSError):
        logger.exception("Error de configuración o de escritura")
        return 1
    finally:
        if conexion is not None:
            conexion.close()
            logger.info("Conexión cerrada")
    logger.info("Ingesta completada en %.2f s", time.perf_counter() - inicio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
