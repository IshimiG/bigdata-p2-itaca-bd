"""Logger propio de la ingesta.

crear_logger(nombre) devuelve un logger con:
  - salida a consola;
  - fichero rotativo logs/ingesta.log en la raíz del proyecto (1 MB, 3 copias);
  - formato fecha / nivel / módulo;
  - nivel configurable con la variable de entorno LOG_LEVEL (por defecto INFO).
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_LOGS = RAIZ / "logs"
FICHERO_LOG = DIR_LOGS / "ingesta.log"
FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
NIVELES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def crear_logger(nombre: str) -> logging.Logger:
    logger = logging.getLogger(nombre)
    if logger.handlers:  # ya configurado: no duplicar mensajes
        return logger
    nivel = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    if nivel not in NIVELES:
        nivel = "INFO"
    logger.setLevel(nivel)
    logger.propagate = False

    formato = logging.Formatter(FORMATO)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    logger.addHandler(consola)

    DIR_LOGS.mkdir(exist_ok=True)
    fichero = RotatingFileHandler(FICHERO_LOG, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fichero.setFormatter(formato)
    logger.addHandler(fichero)
    return logger
