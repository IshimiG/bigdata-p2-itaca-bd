"""Logger propio de la ingesta.

crear_logger(nombre) devuelve un logger con:
  - salida a consola;
  - fichero rotativo logs/ingesta.log (1 MB, 3 copias);
  - formato fecha / nivel / módulo;
  - nivel configurable con la variable de entorno LOG_LEVEL (por defecto INFO).
"""
import logging
import os
from logging.handlers import RotatingFileHandler

DIR_LOGS = "logs"
FICHERO_LOG = os.path.join(DIR_LOGS, "ingesta.log")
FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def crear_logger(nombre: str) -> logging.Logger:
    logger = logging.getLogger(nombre)
    if logger.handlers:  # ya configurado: no duplicar mensajes
        return logger
    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    if nivel not in logging.getLevelNamesMapping():
        nivel = "INFO"
    logger.setLevel(nivel)
    logger.propagate = False

    formato = logging.Formatter(FORMATO)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    logger.addHandler(consola)

    os.makedirs(DIR_LOGS, exist_ok=True)
    fichero = RotatingFileHandler(FICHERO_LOG, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fichero.setFormatter(formato)
    logger.addHandler(fichero)
    return logger
