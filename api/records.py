"""Ronda 23: récords por semilla. Persistencia en un JSON local (fuera del control de versiones).

- Carpeta de datos: la variable de entorno ARES_DATOS_DIR o, si no existe, `datos_local/` en la raíz del proyecto.
- Escritura atómica (archivo temporal + os.replace) y tolerante a un archivo corrupto: se aparta como `.corrupto` y se
  empieza de cero, sin romper la partida.
- Sin dependencias del motor: funciones puras sobre listas de diccionarios, para probarlas solas.
"""
import json
import os
import threading
import uuid
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRE_ARCHIVO = "records.json"
MAX_REGISTROS = 20000
ORIGENES = ("manual", "asistida", "ia")
_candado = threading.Lock()


def carpeta_datos() -> str:
    return os.environ.get("ARES_DATOS_DIR") or os.path.join(RAIZ, "datos_local")


def ruta_archivo() -> str:
    return os.path.join(carpeta_datos(), NOMBRE_ARCHIVO)


def cargar() -> list:
    """Lista de registros guardados. Archivo ausente, vacío o corrupto: lista vacía (el corrupto se aparta)."""
    ruta = ruta_archivo()
    if not os.path.exists(ruta):
        return []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        lista = datos.get("records") if isinstance(datos, dict) else None
        if not isinstance(lista, list):
            raise ValueError("estructura inesperada")
        return [r for r in lista if _valido(r)]
    except (OSError, ValueError):
        try:
            os.replace(ruta, ruta + ".corrupto")
        except OSError:
            pass
        return []


def _valido(r) -> bool:
    return isinstance(r, dict) and all(k in r for k in ("semilla", "planeta", "nivel", "resultado", "pasos", "puntaje"))


def _guardar(lista: list) -> None:
    carpeta = carpeta_datos()
    os.makedirs(carpeta, exist_ok=True)
    ruta = ruta_archivo()
    temporal = f"{ruta}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "records": lista[-MAX_REGISTROS:]}, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, ruta)
    finally:
        if os.path.exists(temporal):
            try:
                os.remove(temporal)
            except OSError:
                pass


def config_de(r: dict) -> tuple:
    """Lo que hace «el mismo mapa y las mismas condiciones»: planeta, nivel, tamaño, semilla y vehículo."""
    return (r.get("planeta"), r.get("nivel"), r.get("tamano"), r.get("semilla"), r.get("vehiculo"))


def clave_orden(r: dict) -> tuple:
    """Mejor primero: éxito, más puntaje, menos pasos, más batería, el más antiguo."""
    return (0 if r.get("resultado") == "EXITO" else 1, -float(r.get("puntaje") or 0), int(r.get("pasos") or 0),
            -float(r.get("bateria_pct") or 0), str(r.get("fecha") or ""))


def mejor_de(registros: list, r: dict):
    """Mejor marca de exito con la misma configuración y el mismo origen que `r` (None si no hay)."""
    previos = [x for x in registros if config_de(x) == config_de(r) and x.get("origen") == r.get("origen")
               and x.get("resultado") == "EXITO"]
    return min(previos, key=clave_orden) if previos else None


def registrar(nuevo: dict) -> dict:
    """Guarda el registro y dice si es récord: éxito y mejor que la marca anterior de su configuración y origen."""
    with _candado:
        lista = cargar()
        anterior = mejor_de(lista, nuevo)
        nuevo = {**nuevo, "id": uuid.uuid4().hex[:10], "fecha": datetime.now().isoformat(timespec="seconds")}
        es_record = nuevo["resultado"] == "EXITO" and (anterior is None or clave_orden(nuevo) < clave_orden(anterior))
        lista.append(nuevo)
        _guardar(lista)
        mismos = sorted([x for x in lista if config_de(x) == config_de(nuevo) and x.get("origen") == nuevo.get("origen")
                         and x.get("resultado") == "EXITO"], key=clave_orden)
        puesto = next((i + 1 for i, x in enumerate(mismos) if x["id"] == nuevo["id"]), None)
        return {"record": nuevo, "nuevo_record": bool(es_record), "mejor_anterior": anterior, "puesto": puesto,
                "intentos": sum(1 for x in lista if config_de(x) == config_de(nuevo))}


def borrar_todos() -> int:
    with _candado:
        n = len(cargar())
        _guardar([])
        return n


def consultar(filtros: dict, limite: int = 200) -> dict:
    """Mejores marcas (una por configuración y origen) y la lista de intentos, con filtros opcionales."""
    todos = cargar()

    def pasa(r):
        for campo in ("planeta", "nivel", "tamano", "semilla", "vehiculo", "origen", "resultado"):
            v = filtros.get(campo)
            if v is None or v == "":
                continue
            if str(r.get(campo)) != str(v):
                return False
        return True

    filtrados = [r for r in todos if pasa(r)]
    grupos = {}
    for r in filtrados:
        grupos.setdefault(config_de(r) + (r.get("origen"),), []).append(r)
    mejores = []
    for lista in grupos.values():
        lista.sort(key=clave_orden)
        mejores.append({**lista[0], "intentos": len(lista), "exitos": sum(1 for x in lista if x["resultado"] == "EXITO")})
    mejores.sort(key=clave_orden)
    filtrados.sort(key=clave_orden)
    return {"total": len(todos), "filtrados": len(filtrados), "mejores": mejores[:limite], "records": filtrados[:limite],
            "planetas": sorted({str(r.get("planeta")) for r in todos}),
            "niveles": sorted({r.get("nivel") for r in todos if isinstance(r.get("nivel"), int)})}


def origen_de(historial: list) -> str:
    """«manual» (solo las manos del jugador), «asistida» (manual con la IA conduciendo en algún tramo, o humano e IA
    mezclados) o «ia» (la conducción fue de un modo de la IA desde el principio), según la bitácora de la partida."""
    humano = ia_en_manual = ia_pura = 0
    for f in historial:
        tec, modo = f.get("tecnica"), f.get("modo")
        if tec == "humano":
            humano += 1
        elif tec == "escenario":
            continue
        elif modo == "manual":
            ia_en_manual += 1
        else:
            ia_pura += 1
    if humano == 0 and ia_en_manual == 0:
        return "ia" if ia_pura else "manual"
    if ia_en_manual or ia_pura:
        return "asistida"
    return "manual"
