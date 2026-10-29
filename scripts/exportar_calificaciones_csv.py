#!/usr/bin/env python3
"""Exporta calificaciones a un CSV por año: <salida>/calificaciones_AAAA.csv.

Incremental: los años que ya tienen su CSV se saltan. Con --rehacer se regeneran.
Conexión por variables de entorno: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
(por defecto, la base local de scripts/levantar.sh).
Requiere: pandas, psycopg2-binary.
"""
import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_DEFECTO = RAIZ / "data" / "csv"

COLUMNAS = [
    "evaluacion", "alumno", "ensenanza", "curso", "contenido",
    "bloque_contenido", "nota_numerica", "tipo_nota", "anyo",
]
QUERY = f"""
    SELECT {", ".join(COLUMNAS)}
    FROM calificaciones
    WHERE anyo = %s
    ORDER BY alumno, curso, evaluacion, contenido
"""


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "dev"),
        user=os.getenv("DB_USER", "ishimi"),
        password=os.getenv("DB_PASSWORD"),
    )


def main():
    ap = argparse.ArgumentParser(description="Exporta calificaciones a un CSV por año.")
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFECTO)
    ap.add_argument("--rehacer", action="store_true", help="regenera también los años ya exportados")
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    conexion = conectar()
    try:
        with conexion.cursor() as cur:
            cur.execute("SELECT DISTINCT anyo FROM calificaciones WHERE anyo IS NOT NULL ORDER BY anyo")
            anyos = [fila[0] for fila in cur.fetchall()]

        for anyo in anyos:
            destino = args.salida / f"calificaciones_{anyo}.csv"
            if destino.exists() and not args.rehacer:
                print(f"SALTADO   {destino.name} (ya exportado)")
                continue
            df = pd.read_sql(QUERY, conexion, params=(anyo,))
            # Se escribe a un temporal y se renombra al final: un corte a medias no deja un CSV incompleto.
            tmp = destino.with_suffix(".csv.tmp")
            df.to_csv(tmp, index=False)
            tmp.replace(destino)
            print(f"EXPORTADO {destino.name} ({len(df)} filas)")
    finally:
        conexion.close()


if __name__ == "__main__":
    main()
