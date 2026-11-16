"""Partida sin ventana desde la línea de comandos (para revisar capturas y resultados).

Uso (desde ares_x/):
    python -m juego --headless --semilla 11 --pasos 300 --salida salida_juego

Hace, en orden:
1. Corre la partida con la IA (SDL_VIDEODRIVER=dummy, sin ventana).
2. Dispara eventos programados (barranco al paso 5, falla de sensor al 10, tormenta al 15) para
   que las capturas y el registro muestren cada evento.
3. Guarda las capturas de escenas clave en <salida>/capturas/.
4. Escribe el CSV de la bitácora y el JSON de la configuración y el resumen en <salida>/.
5. Imprime una línea final con el resultado: llegó o no, puntaje, pasos y eventos.
"""
import argparse
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from juego.partida import Partida  # noqa: E402
from juego.exportar import exportar_partida  # noqa: E402

EVENTOS_PROGRAMADOS = {5: "barranco", 10: "falla_sensor", 15: "tormenta"}


def correr(semilla, pasos, salida, nivel=1, capturas=True):
    """Corre una partida sin ventana. Devuelve un diccionario con el resultado."""
    partida = Partida(semilla=semilla, nivel=nivel)
    eventos = []
    for paso in range(1, pasos + 1):
        if paso in EVENTOS_PROGRAMADOS and partida.estado not in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            nombre = EVENTOS_PROGRAMADOS[paso]
            r = partida.disparar_evento(nombre)
            eventos.append(f"{paso}:{nombre}:{'ok' if r.get('ok') else 'no'}")
        if partida.estado in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
            break
        partida.avanzar_ia()

    rutas_datos = {}
    if capturas:
        from juego.capturas import generar_capturas
        rutas_datos["capturas"] = generar_capturas(semilla=semilla, carpeta=os.path.join(salida, "capturas"))
    csv_ruta, json_ruta = exportar_partida(partida, salida)
    llego = partida.estado == "EXITO"
    puntaje = partida.puntaje()
    resumen = partida.resumen()
    return {
        "llego": llego, "estado": partida.estado, "puntaje": puntaje,
        "pasos": resumen.get("pasos"), "eventos": eventos,
        "csv": csv_ruta, "json": json_ruta, **rutas_datos,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="ARES-X: partida sin ventana")
    parser.add_argument("--headless", action="store_true", help="correr sin ventana (requerido)")
    parser.add_argument("--semilla", type=int, default=11)
    parser.add_argument("--pasos", type=int, default=300)
    parser.add_argument("--nivel", type=int, default=1)
    parser.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "salida_headless"))
    parser.add_argument("--sin-capturas", action="store_true", help="no guardar capturas (más rápido)")
    args = parser.parse_args(argv)
    if not args.headless:
        parser.error("este punto de entrada corre solo con --headless; para la ventana usa python juego/main.py")

    res = correr(args.semilla, args.pasos, args.salida, nivel=args.nivel, capturas=not args.sin_capturas)
    llego = "SI" if res["llego"] else "NO"
    eventos = ",".join(res["eventos"]) if res["eventos"] else "ninguno"
    print(f"RESULTADO llego={llego} estado={res['estado']} puntaje={res['puntaje']} "
          f"pasos={res['pasos']} eventos=[{eventos}] salida={args.salida}")
    if "capturas" in res:
        for nombre, ruta in res["capturas"].items():
            print(f"captura {nombre}: {ruta}")
    print(f"csv: {res['csv']}")
    print(f"json: {res['json']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
