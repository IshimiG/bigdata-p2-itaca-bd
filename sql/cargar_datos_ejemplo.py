"""Carga datos de ejemplo en la réplica PostgreSQL a partir de los XML de la P1.

Es solo para montar el entorno de desarrollo (en producción la réplica ya existe).
Usa el usuario PROPIETARIO (DB_ADMIN_USER), no el de lectura. Los XML de ejemplo ya vienen
anonimizados por el docente. Uso:  python sql/cargar_datos_ejemplo.py [ruta/exportaciones]
"""
import os
import sys
import xml.etree.ElementTree as ET

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extras import execute_values

RUTA_POR_DEFECTO = "../bigdata-p1-itaca/data/exportaciones"

# tabla -> (etiqueta XML, columnas) en el orden de carga (primero las referenciadas por FK)
TABLAS = {
    "cursos": ("curso", ["codigo", "nombre_cas", "nombre_val", "abreviatura", "ensenanza", "padre"]),
    "grupos": ("grupo", ["codigo", "nombre", "turno", "linea", "modalidad"]),
    "contenidos": ("contenido", ["codigo", "nombre_cas", "nombre_val", "ensenanza", "curso"]),
    "alumnos": ("alumno", ["NIA", "sexo", "nacionalidad", "provincia", "municipio", "ensenanza", "curso",
                           "grupo", "turno", "linea", "modalidad", "repite", "estado_matricula",
                           "tipo_matricula", "fecha_matricula", "fecha_ingreso_centro"]),
    "calificaciones": ("calificacion", ["evaluacion", "alumno", "ensenanza", "curso", "contenido",
                                        "bloque_contenido", "nota_numerica", "tipo_nota"]),
}


def leer(ruta: str, etiqueta: str, campos: list[str]) -> list[tuple]:
    raiz = ET.parse(ruta).getroot()
    anyo = raiz.get("curso")
    filas = []
    for nodo in raiz.iter(etiqueta):
        valores = [(nodo.get(c) or "").strip() or None for c in campos]
        filas.append((anyo, *valores))
    return filas


def main() -> int:
    load_dotenv()
    base = sys.argv[1] if len(sys.argv) > 1 else RUTA_POR_DEFECTO
    if not os.path.isdir(base):
        print(f"No existe {base}", file=sys.stderr)
        return 1
    try:
        con = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "itaca_academico"),
            user=os.environ["DB_ADMIN_USER"], password=os.environ["DB_ADMIN_PASSWORD"])
    except (KeyError, psycopg2.Error) as e:
        print(f"No se puede conectar como propietario: {e}", file=sys.stderr)
        return 1
    try:
        with con, con.cursor() as cur:
            cur.execute("TRUNCATE alumnos, calificaciones, contenidos, grupos, cursos RESTART IDENTITY")
            for tabla, (etiqueta, campos) in TABLAS.items():
                total = 0
                for curso in sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))):
                    filas = leer(os.path.join(base, curso, f"{tabla}.xml"), etiqueta, campos)
                    columnas = sql.SQL(", ").join(sql.Identifier(c) for c in ["anyo", *campos])
                    execute_values(cur, sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                        sql.Identifier(tabla), columnas), filas, page_size=5000)
                    total += len(filas)
                print(f"{tabla}: {total} filas")
    except (psycopg2.Error, ET.ParseError, OSError) as e:
        print(f"Error en la carga (se deshace todo): {e}", file=sys.stderr)
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
