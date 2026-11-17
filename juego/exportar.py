"""ARES-X · Exportación de una partida a CSV (bitácora) y JSON (configuración + resumen).

Parámetros de simulación ficticios, no especificaciones NASA.
Contrato: juego/CONTRATO.md. Nunca sobrescribe archivos existentes.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np

from simulador import BARRANCO, OBSTACULO

PLANETA = "Marte"
NOTA = "parámetros de simulación ficticios, no especificaciones NASA"
BATERIA_INICIAL_POR_DEFECTO = 100.0
VERSION_CONSTANTE = "ares-x-juego-1.0"   # respaldo cuando git no está disponible (ARX-89a)


def _version_software() -> tuple[str, str]:
    """Versión del software: hash de git de HEAD si se puede leer; si no, la constante.

    Devuelve (versión, origen) con origen "git" o "constante".
    """
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(Path(__file__).resolve().parent),
                           capture_output=True, text=True, timeout=5)
        h = r.stdout.strip()
        if r.returncode == 0 and len(h) == 40 and all(c in "0123456789abcdef" for c in h):
            return h, "git"
    except (OSError, subprocess.SubprocessError):
        pass
    return VERSION_CONSTANTE, "constante"


def _metricas(partida) -> dict:
    """Métricas completas leídas de atributos existentes; None si el objeto no los tiene.

    - energia_restante: rover.bateria
    - distancia_recorrida: rover.distancia_recorrida (celdas movidas)
    - sitios_visitados_celdas: celdas de los sitios visitados (mision.visitados)
    - puntaje_sitios: valor de esos sitios en mundo.sitios (solo si el mundo guarda un número)
    - replanes: mision.replanes
    - tiempo_computo_s: tiempo de pared acumulado de la partida, que el motor guarda desde ARX-89b
      (`juego/partida.py`); None si la partida no lo trae, nunca inventado
    """
    mision = getattr(partida, "mision", None)
    rover = getattr(partida, "rover", None)
    bateria = getattr(rover, "bateria", None)
    dist = getattr(rover, "distancia_recorrida", None)
    visitados = getattr(mision, "visitados", None)
    celdas = None
    puntaje_sitios = None
    if visitados is not None:
        celdas = sorted([int(c[0]), int(c[1])] for c in visitados)
        sitios = getattr(getattr(partida, "mundo", None), "sitios", None)
        if isinstance(sitios, dict):
            valores = [sitios.get(tuple(c)) for c in celdas]
            if all(isinstance(v, (int, float, np.number)) and not isinstance(v, bool) for v in valores):
                puntaje_sitios = float(sum(valores))
    replanes = getattr(mision, "replanes", None)
    tiempo = getattr(partida, "tiempo_computo_s", None)
    return {
        "energia_restante": None if bateria is None else round(float(bateria), 1),
        "distancia_recorrida": None if dist is None else int(dist),
        "sitios_visitados_celdas": celdas,
        "puntaje_sitios": puntaje_sitios,
        "replanes": None if replanes is None else int(replanes),
        "tiempo_computo_s": None if tiempo is None else float(tiempo),
    }


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
    version, origen = _version_software()
    return {
        "semilla": int(mundo.semilla),
        "planeta": PLANETA,
        "n_obstaculos": int(np.count_nonzero(tipo == OBSTACULO)),
        "n_barrancos": int(np.count_nonzero(tipo == BARRANCO)),
        "n_sitios": int(len(mundo.sitios)),
        "bateria_inicial": float(bateria),
        "version_software": version,
        "version_origen": origen,
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
    # Solo añade: las claves que el motor ya da no se tocan (ARX-89a)
    for clave, valor in _metricas(partida).items():
        resumen.setdefault(clave, valor)

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
