"""ARES-X · Exportación de una partida a CSV (bitácora) y JSON (configuración + resumen).

Parámetros de simulación ficticios, no especificaciones NASA.
Contrato: juego/CONTRATO.md. Nunca sobrescribe archivos existentes.
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from simulador import BARRANCO, OBSTACULO

PLANETA = "Marte"
NOTA = "parámetros de simulación ficticios, no especificaciones NASA"
BATERIA_INICIAL_POR_DEFECTO = 100.0


def _json_seguro(valor):
    """Convierte tipos de numpy y otros a tipos nativos de JSON."""
    if isinstance(valor, np.generic):
        return valor.item()
    if isinstance(valor, np.ndarray):
        return valor.tolist()
    if isinstance(valor, (tuple, set)):
        return list(valor)
    return str(valor)


def _configuracion(partida) -> dict:
    """Configuración de la partida leída del objeto (atributos opcionales con respaldo en el mundo)."""
    mundo = partida.mundo
    tipo = np.asarray(mundo.tipo)
    # Partida guarda la batería inicial en su Mision (partida.mision.bateria_inicial)
    mision = getattr(partida, "mision", None)
    bateria = getattr(partida, "bateria_inicial", None)
    if bateria is None:
        bateria = getattr(mision, "bateria_inicial", BATERIA_INICIAL_POR_DEFECTO)
    return {
        "semilla": int(mundo.semilla),
        "planeta": PLANETA,
        "n_obstaculos": int(np.count_nonzero(tipo == OBSTACULO)),
        "n_barrancos": int(np.count_nonzero(tipo == BARRANCO)),
        "n_sitios": int(len(mundo.sitios)),
        "bateria_inicial": float(bateria),
    }


def _crear_exclusivo(ruta: Path, escribir) -> None:
    """Crea el archivo solo si no existe (modo 'x') y lo escribe con la función dada."""
    with open(ruta, "x", encoding="utf-8", newline="") as f:
        escribir(f)


def exportar_partida(partida, carpeta: str) -> tuple[str, str]:
    """Escribe <carpeta>/partida_<semilla>_<hora>.csv (bitácora) y .json (configuración + resumen).

    Devuelve las dos rutas. Crea la carpeta si no existe. Nunca sobrescribe: si el nombre
    base ya existe, se añade el sufijo _2, _3, ... al par de archivos.
    """
    config = _configuracion(partida)
    bitacora = partida.bitacora()
    resumen = partida.resumen()

    carpeta_path = Path(carpeta)
    carpeta_path.mkdir(parents=True, exist_ok=True)

    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = f"partida_{config['semilla']}_{marca}"
    contenido_json = json.dumps(
        {**config, "resumen": resumen, "nota": NOTA},
        ensure_ascii=False, indent=2, default=_json_seguro,
    )

    n = 1
    while True:
        nombre = base if n == 1 else f"{base}_{n}"
        ruta_csv = carpeta_path / f"{nombre}.csv"
        ruta_json = carpeta_path / f"{nombre}.json"
        try:
            _crear_exclusivo(ruta_csv, lambda f: bitacora.to_csv(f, index=False))
        except FileExistsError:
            n += 1
            continue
        try:
            _crear_exclusivo(ruta_json, lambda f: f.write(contenido_json))
        except FileExistsError:
            ruta_csv.unlink()   # no dejar un CSV huérfano del par
            n += 1
            continue
        return str(ruta_csv), str(ruta_json)
