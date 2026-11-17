"""Regeneración única de cifras (ev3-d64 A): corre en serie los scripts que publican las cifras de docs/.

Uso (desde la raíz del repositorio):
    python scripts/regenerar_todo.py [--log RUTA]

Pasos, uno detrás de otro, un proceso a la vez:
    1. congelado: comparacion_politicas.py 20 congelado   -> docs/COMPARACION_POLITICAS.json
    2. exigente:  comparacion_politicas.py 20 exigente    -> docs/COMPARACION_POLITICAS_exigente.json
    2b. exigente10: comparacion_politicas.py 20 exigente10 -> docs/COMPARACION_POLITICAS_exigente10.json (ARX-92c)
    3. traza:     traza_divergencias.py 20 exigente       -> docs/TRAZA_DIVERGENCIAS_exigente.csv
    4. tabla:     tabla_modos.py                           -> docs/tabla_modos.csv y docs/TABLA_MODOS.md
    5. rejilla:   rejilla_resbalon.py --salida docs        -> docs/REJILLA_RESBALON_exigente.{json,csv}

medir_tiempos (ARX-44) no está en esta rama: su medición de 20 semillas ya está en b787fdb y no depende
de las cifras; se registra como OMITIDO en el log.

El log escribe la hora de inicio y fin de cada paso y el código de salida. Si un paso falla, la tanda se
detiene y no lanza los siguientes. Nada se confirma (commit): eso se hace tras revisar los resultados.
"""
import datetime
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASOS = [
    ("congelado", [sys.executable, "scripts/comparacion_politicas.py", "20", "congelado"]),
    ("exigente", [sys.executable, "scripts/comparacion_politicas.py", "20", "exigente"]),
    ("exigente10", [sys.executable, "scripts/comparacion_politicas.py", "20", "exigente10"]),
    ("traza_exigente", [sys.executable, "scripts/traza_divergencias.py", "20", "exigente"]),
    ("tabla_modos", [sys.executable, "scripts/tabla_modos.py"]),
    ("rejilla_resbalon", [sys.executable, "scripts/rejilla_resbalon.py", "--salida", "docs"]),
]
OMITIDOS = [("medir_tiempos", "no está en esta rama; medición de 20 semillas en b787fdb, no depende de las cifras")]


def hora():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    log_path = os.path.join(tempfile.gettempdir(), "regen_cifras_log.txt")
    if "--log" in sys.argv:
        log_path = sys.argv[sys.argv.index("--log") + 1]
    with open(log_path, "a", encoding="utf-8") as log:
        def escribir(texto):
            print(texto, flush=True)
            log.write(texto + "\n")
            log.flush()

        escribir(f"== regeneración única inicio {hora()} raíz {RAIZ}")
        for nombre, _ in OMITIDOS:
            escribir(f"OMITIDO {nombre}: {dict(OMITIDOS)[nombre]}")
        for nombre, orden in PASOS:
            escribir(f"-> {nombre} inicio {hora()}: {' '.join(orden[1:])}")
            codigo = subprocess.call(orden, cwd=RAIZ)
            escribir(f"<- {nombre} fin {hora()} código {codigo}")
            if codigo != 0:
                escribir(f"DETENIDO en {nombre}: no se lanzan los pasos siguientes.")
                return codigo
        escribir(f"== regeneración única fin {hora()}: todos los pasos OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
