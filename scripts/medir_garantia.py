"""ARX-79a: medición de la garantía de partida ganable (garantia=True), sin eventos, modo automático.

Corre las partidas por la API en proceso (TestClient: sin servidores, sin red), una a la vez, con semillas 1..N por
nivel y tope de 500 pasos. Clasifica la causa de cada derrota y escribe todas las filas en JSON.

Uso (desde la raíz del repositorio; es medición pesada, pedir turno):
    python scripts/medir_garantia.py grande  [semillas=20] [niveles=1,2,3,4,5] [salida.json]
    python scripts/medir_garantia.py pequeno [semillas=20] [niveles=1,2,3,4,5] [salida.json]
Ejemplo completo de 79a:
    python scripts/medir_garantia.py grande 20 1,2,3,4,5 && python scripts/medir_garantia.py pequeno 20 1,2,3,4,5

Salida: por defecto docs/planes/mediciones/medicion_garantia_<tamano>.json (se crea la carpeta); la tabla en
markdown sale por la consola para pegarla en docs/planes/ARX-79_calibracion.md. Tiempo orientativo: grande ~25 min,
pequeño ~5 min de un núcleo.
"""
import json, statistics, sys, time
from collections import Counter
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
tam = sys.argv[1]
n_sem = int(sys.argv[2]) if len(sys.argv) > 2 else 20
niveles = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else [1, 2, 3, 4, 5]
salida = Path(sys.argv[4]) if len(sys.argv) > 4 else repo / "docs" / "planes" / "mediciones" / f"medicion_garantia_{tam}.json"
salida.parent.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))
from fastapi.testclient import TestClient
from api.servidor import crear_app
from integracion import ESTADOS_TERMINALES

MAX_PASOS = 500


def causa(p, c, pasos):
    if p.estado == "EXITO":
        return "EXITO"
    falta_sitios = len(p.mundo.sitios) - len(p.mision.visitados)
    vivos = sum(1 for d in c.drones if d.vivo)
    bat0 = p.rover.bateria <= 0
    import unicodedata
    av = unicodedata.normalize("NFD", " | ".join(p.avisos[-3:])).encode("ascii", "ignore").decode().lower()
    if p.estado not in ESTADOS_TERMINALES:
        if vivos and falta_sitios == 0:
            return "caza parada (sin terminar en %d pasos)" % MAX_PASOS
        return "otra: sin terminar en %d pasos" % MAX_PASOS
    if p.estado == "SIN_RUTA":
        return "SIN_RUTA"
    if falta_sitios and bat0:
        return "bateria 0 con sitios pendientes"
    if falta_sitios and "bateria insuficiente" in av:
        return "bateria insuficiente para sitios restantes"
    if falta_sitios and "sin ruta" in av:
        return "sitios 0/n: sin ruta real a sitios"
    if falta_sitios == 0 and vivos and ("bateria" in av or bat0):
        return "caza sin bateria"
    if falta_sitios == 0 and vivos and "ninguno tiene ruta" in av:
        return "caza sin ruta"
    if falta_sitios == 0 and vivos and ("no se alcanzaron" in av or "municion" in av):
        return "caza: " + p.avisos[-1]
    return "otra: " + (p.avisos[-1] if p.avisos else p.estado)


filas = []
t0 = time.time()
for nivel in niveles:
    for sem in range(1, n_sem + 1):
        app = crear_app()
        cli = TestClient(app)
        t1 = time.time()
        r = cli.post("/partida", json={"semilla": sem, "nivel": nivel, "tamano": tam})
        assert r.status_code == 200, r.text
        t_gen = time.time() - t1
        cli.post("/modo", json={"modo": "automatico"})
        s = app.state.sesion
        p, c = s.partida, s.combate
        pasos = 0
        while pasos < MAX_PASOS and p.estado not in ESTADOS_TERMINALES:
            rr = cli.post("/paso")
            if rr.status_code != 200:
                break
            pasos += 1
        filas.append({"nivel": nivel, "semilla": sem, "estado": p.estado, "exito": p.estado == "EXITO",
                      "pasos": pasos, "bateria_final": round(float(p.rover.bateria), 1),
                      "sitios": f"{len(p.mision.visitados)}/{len(p.mundo.sitios)}",
                      "drones_vivos": sum(1 for d in c.drones if d.vivo), "variante_mapa": p.semilla_mundo,
                      "t_generacion_s": round(t_gen, 2), "causa": causa(p, c, pasos),
                      "avisos": p.avisos[-3:]})
        print(nivel, sem, filas[-1]["estado"], pasos, filas[-1]["causa"], flush=True)
        json.dump(filas, open(salida, "w"), ensure_ascii=False, indent=1)

print(f"\n## Tamano {tam}: {len(filas)} partidas en {time.time()-t0:.0f} s")
print("| Nivel | Exito | Pasos media | Pasos mediana | Causas de derrota |\n|---|---|---|---|---|")
for nivel in niveles:
    f = [x for x in filas if x["nivel"] == nivel]
    ok = [x["pasos"] for x in f if x["exito"]]
    cs = Counter(x["causa"] for x in f if not x["exito"])
    sem_perd = [x["semilla"] for x in f if not x["exito"]]
    print(f"| {nivel} | {len(ok)}/{len(f)} | {statistics.mean(ok):.1f} | {statistics.median(ok):.1f} | "
          f"{'; '.join(f'{k}: {v}' for k, v in cs.items()) or '-'} (semillas {sem_perd}) |" if ok else
          f"| {nivel} | 0/{len(f)} | - | - | {dict(cs)} |")
