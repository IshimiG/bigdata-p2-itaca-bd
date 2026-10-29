"""Genera docs/captura-ejecucion.png y docs/captura-raw.png.

Son RENDERS (Pillow) de la salida real de los comandos: este script ejecuta los comandos,
recoge su salida y la dibuja como un terminal. No son capturas de pantalla.
No lee .env ni la sal: solo ejecuta la ingesta y lee data/raw/.

Uso, desde cualquier carpeta:  .venv/bin/python tools/render_captura.py
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
FUENTES = ["/usr/share/fonts/TTF/JetBrainsMonoNerdFontMono-Regular.ttf",
           "/usr/share/fonts/TTF/DejaVuSansMono.ttf"]
TAM, MARGEN, ALTO_LINEA = 15, 18, 21
FONDO, TEXTO, PROMPT = (30, 32, 40), (220, 223, 228), (120, 200, 140)
# claves no personales que se muestran de cada tabla (sin nombres, fechas ni contactos)
CLAVES = {"alumnos": ["nia", "ensenanza", "curso", "anyo"],
          "calificaciones": ["alumno", "evaluacion", "contenido", "nota_numerica", "anyo"]}


def ejecutar(comando: str) -> str:
    r = subprocess.run(comando, shell=True, cwd=RAIZ, capture_output=True, text=True)
    return (r.stdout + r.stderr).rstrip("\n")


def nia_comun() -> str:
    """Primer NIA anonimizado (por orden) que está en alumnos y en calificaciones."""
    def hashes(prefijo, campo):
        ruta = next((RAIZ / "data" / "raw").glob(f"{prefijo}_*.json"))
        return [r[campo] for r in json.loads(ruta.read_text(encoding="utf-8"))]
    ca = set(hashes("calificaciones", "alumno"))
    return next(h for h in hashes("alumnos", "nia") if h in ca)


def consulta(tabla: str, campo: str, nia: str) -> str:
    """Comando real que muestra una fila de la tabla con solo claves no personales."""
    codigo = (f"import json,glob;d=json.load(open(glob.glob('data/raw/{tabla}_*.json')[0]));"
              f"f=next(r for r in d if r['{campo}']=='{nia}');"
              f"print(json.dumps({{k:f[k] for k in {CLAVES[tabla]}}},ensure_ascii=False))")
    return f'python -I -c "{codigo}"'


def dibujar(bloques: list[tuple[str, str]], destino: Path) -> None:
    """bloques = [(comando, salida)] -> PNG con aspecto de terminal."""
    for ruta in FUENTES:
        if Path(ruta).exists():
            fuente = ImageFont.truetype(ruta, TAM)
            break
    else:
        fuente = ImageFont.load_default()
    lineas = []
    for comando, salida in bloques:
        lineas.append(("$ " + comando, PROMPT))
        lineas += [(l, TEXTO) for l in salida.splitlines()]
        lineas.append(("", TEXTO))
    ancho = max(int(fuente.getlength(t)) for t, _ in lineas) + 2 * MARGEN
    img = Image.new("RGB", (ancho, len(lineas) * ALTO_LINEA + 2 * MARGEN), FONDO)
    d = ImageDraw.Draw(img)
    for n, (texto, color) in enumerate(lineas):
        d.text((MARGEN, MARGEN + n * ALTO_LINEA), texto, font=fuente, fill=color)
    img.save(destino)


def main() -> None:
    python = f"{sys.executable}"
    cmd = f"cd bigdata-p2-itaca-bd && python ingesta/ingesta_itaca_bd.py"
    salida = ejecutar(f"{python} ingesta/ingesta_itaca_bd.py 2>&1; echo \"código de salida: $?\"")
    # rutas del equipo fuera de la imagen y del texto guardado
    salida = salida.replace(str(RAIZ) + "/", "")
    (RAIZ / "docs" / "salida-ingesta.txt").write_text(salida + "\n", encoding="utf-8")
    dibujar([(cmd, salida)], RAIZ / "docs" / "captura-ejecucion.png")

    nia = nia_comun()
    bloques = [("ls -l data/raw", ejecutar("ls -l data/raw")),
               ("# misma persona, mismo hash, en las dos tablas (solo claves no personales)", "")]
    for tabla, campo in (("alumnos", "nia"), ("calificaciones", "alumno")):
        c = consulta(tabla, campo, nia)
        bloques.append((c, ejecutar(c)))
    dibujar(bloques, RAIZ / "docs" / "captura-raw.png")
    print("Generadas docs/captura-ejecucion.png y docs/captura-raw.png")


if __name__ == "__main__":
    main()
