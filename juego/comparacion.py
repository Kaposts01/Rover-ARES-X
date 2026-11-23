"""Comparación de políticas (RF-14, RF-15, CA-08): híbrido frente a sin RNA, sin difuso y sin AG.

Mismas semillas para todas las variantes. Cada variante es una partida de la capa de juego con una sola técnica
desactivada (o el AG reemplazado):
- hibrido:    el controlador completo (avanzar_ia).
- sin_rna:    la RNA no interviene (probabilidades neutras); el supervisor sigue activo.
- sin_difuso: velocidad fija de 0,5, sin controlador difuso.
- sin_ag_vecino:      (ARX-92d, antes «sin_ag») el orden de visita lo elige el vecino más cercano, no el AG; ruta BFS.
- sin_ag_mas_corta:  (ARX-92d) el orden lo elige el envoltorio con pesos solo de distancia: la permutación más corta.

- ruta_corta:  línea base (ARX-45, M19): mapa de riesgo en ceros (no conoce peligros), sin RNA ni difuso, sitios por
               vecino más cercano y ruta BFS (la más corta). El sensor sigue marcando lo que ve y el supervisor veta.

- ag_puro:     línea base (ARX-45, M19): AG intacto con el mapa de riesgo FIJO (el inicial del escenario), sin RNA ni
               difuso. Decisión del Orquestador (opción C): el mapa se congela desde este módulo, sobre la instancia,
               restaurando el snapshot inicial tras cada paso_mision; lo que el sensor marque en un paso solo vale
               dentro de ese paso (el supervisor sigue activo). No se toca integracion.py.

Métricas por variante: éxito, pasos, colisiones y energía final; media, mediana, desviación típica y rango
intercuartílico (dispersión). La comparación no atribuye causalidad fuera de estas condiciones (§14).
"""
import numpy as np

from genetico import camino_bfs, mapa_estimado
from integracion import ESTADOS_TERMINALES, Mision

VARIANTES_ABLACION = ("hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_mas_corta", "sin_ag_2opt")   # ARX-28, 92d y 92c
VARIANTES_BASE = ("ruta_corta", "ag_puro")                              # ARX-45 (M19)
VARIANTES = VARIANTES_ABLACION + VARIANTES_BASE
# R23: variantes del escenario jugable difícil (partida con plan restringido). `sin_ag_*` usan la heurística en vez del AG, con el
# mismo ejecutor y la misma reparación de recargas; `difuso_base` es el difuso por defecto (sin evolucionar) con todo lo demás igual.
VARIANTES_JUGABLE = ("hibrido", "sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_2opt", "sin_ag_ventanas", "difuso_base")
MAX_PASOS = 400

# Escenarios de evaluación (ARX-28b). R23b: los de la partida actual primero; `INFO_ESCENARIOS` dice cuál es histórico.
ESCENARIOS = {
    # R23b: primero los escenarios que representan el juego actual; el congelado es histórico (versión anterior del juego).
    # R23: la partida jugable difícil (garantia=True): 11 sitios con ventanas de tiempo, recarga obligatoria, sitios opcionales y las
    # mecánicas del planeta (viento, hielo, gravedad). Un escenario por planeta; el híbrido usa el difuso evolucionado del planeta.
    "jugable_dificil": {"nivel": 4, "ruido": None, "p_detectar": None, "prob_fallo": None, "jugable": True,
                        "planeta": "Marte", "n_sitios": 11, "variantes": VARIANTES_JUGABLE},
    "jugable_dificil_neptuno": {"nivel": 4, "ruido": None, "p_detectar": None, "prob_fallo": None, "jugable": True,
                                "planeta": "Neptuno", "n_sitios": 11, "variantes": VARIANTES_JUGABLE},
    # "exigente": nivel 5 con sensor más ruidoso y detección de peligros más pobre. ruido y p_detectar los fijó ARX-28a
    # (calibración; ver docs/planes/ARX-28_calibracion.md). Si alguno fuera None el escenario no se podría usar.
    # prob_fallo (ev3-d60 A): probabilidad de lectura NaN del sensor de proximidad, solo en este escenario. None = sin fallo.
    "exigente": {"nivel": 5, "ruido": 0.6, "p_detectar": 0.4, "prob_fallo": None, "fisica_velocidad": True},         # calibrado en ARX-28a (docs/planes/ARX-28_calibracion.md)
    # ARX-92c (ev3-d73 A): 10 sitios y batería = ⌈L_ref × 1,15⌉ por semilla (criterio en ARX-92_ag_decide.md §12)
    "exigente10": {"nivel": 5, "ruido": 0.6, "p_detectar": 0.4, "prob_fallo": None, "fisica_velocidad": True,
                   "n_sitios": 10, "margen_bateria": 0.15},
    # "congelado" es la evaluación del informe: 20x30, nivel 1, parámetros por defecto. Histórico: ya no representa el juego.
    "congelado": {"nivel": 1, "ruido": None, "p_detectar": None, "prob_fallo": None},      # None = no se toca: valores por defecto de Mision
}

# R23b: lo que se muestra de cada escenario (la API y los JSON de docs/ lo publican; no entra en la salida de `comparar`, cuyo hash
# fija una prueba). `historico`: ya no representa el juego actual.
INFO_ESCENARIOS = {
    "jugable_dificil": {
        "titulo": "Partida jugable difícil en Marte (versión actual)", "historico": False,
        "descripcion": "Nivel 4, mapa pequeño, 11 sitios con ventanas de tiempo, recarga obligatoria en bases, sitios opcionales, "
                       "viento, hielo y polvo de Marte. Es la partida real: el AG ordena los sitios, decide dónde recargar y cuáles "
                       "sacrificar. Sin drones (el laboratorio corre la partida sin combate)."},
    "jugable_dificil_neptuno": {
        "titulo": "Partida jugable difícil en Neptuno (versión actual)", "historico": False,
        "descripcion": "Igual que la de Marte (nivel 4, 11 sitios con ventanas, recargas, opcionales) con viento muy fuerte y hielo "
                       "muy resbaladizo de Neptuno. Sin drones."},
    "exigente": {
        "titulo": "Exigente (nivel 5 con sensor ruidoso, 3 a 4 sitios)", "historico": False,
        "descripcion": "Mapa pequeño, nivel 5, sensor con ruido 0,6 y detección pobre de peligros. NO ejercita al AG restringido: son "
                       "3 a 4 sitios sin ventanas de tiempo ni recargas, y con tan pocos sitios el 2-opt encuentra el mismo orden que el "
                       "AG (las dos políticas hacen exactamente lo mismo en las 20 semillas). Sirve para medir RNA y difuso con "
                       "sensores malos, no al AG."},
    "exigente10": {
        "titulo": "Exigente con 10 sitios (sin ventanas ni recargas)", "historico": False,
        "descripcion": "Como el exigente pero con 10 sitios y batería ajustada a la ruta de referencia. Ejercita el orden de los "
                       "sitios (viajante) pero no las ventanas de tiempo ni las recargas de la partida actual."},
    "congelado": {
        "titulo": "Congelado (histórico: versión anterior del juego)", "historico": True,
        "descripcion": "Histórico (versión anterior del juego): nivel 1, 3 a 4 sitios, sin ventanas, recargas ni mecánicas de "
                       "planeta. Ya no representa la partida actual; se conserva para reproducir la evaluación del informe "
                       "(las pruebas fijan su huella)."},
}


def _orden_2opt(m: Mision):
    """ARX-92c: orden de sitios del vecino más cercano mejorado con 2-opt (intercambio de tramos mientras baje el largo
    de la ruta por BFS). Mapa real con la máscara de riesgo de la misión; sin AG."""
    def planear(origen, pendientes):
        transitable = m.riesgo < 0.5
        largos = {}
        def largo(a, b):
            if (a, b) not in largos:
                t = camino_bfs(a, b, transitable)
                largos[(a, b)] = float("inf") if t is None else len(t) - 1
            return largos[(a, b)]
        ruta_vec = _orden_voraz(m)(origen, pendientes)
        if not ruta_vec:
            return []
        orden = []
        for c in ruta_vec[1:]:
            if c in pendientes and c not in orden:
                orden.append(c)
        seq = [tuple(origen)] + orden + [tuple(m.mundo.refugio)]
        mejora = True
        while mejora:
            mejora = False
            for i in range(1, len(seq) - 2):
                for j in range(i + 1, len(seq) - 1):
                    antes = largo(seq[i - 1], seq[i]) + largo(seq[j], seq[j + 1])
                    despues = largo(seq[i - 1], seq[j]) + largo(seq[i], seq[j + 1])
                    if despues < antes:
                        seq[i:j + 1] = seq[i:j + 1][::-1]
                        mejora = True
        ruta = [seq[0]]
        for a, b in zip(seq, seq[1:]):
            t = camino_bfs(a, b, transitable)
            if t is None:
                return []
            ruta.extend(t[1:])
        return ruta
    return planear


def _orden_voraz(m: Mision):
    """Reemplazo del AG: visita los sitios pendientes por vecino más cercano y une los tramos con BFS."""
    def planear(origen, pendientes):
        transitable = m.riesgo < 0.5
        pts = list(pendientes)
        ruta, cur = [origen], origen
        while pts:
            nxt = min(pts, key=lambda c: max(abs(c[0] - cur[0]), abs(c[1] - cur[1])))
            tramo = camino_bfs(cur, nxt, transitable)
            if tramo is None:
                return []
            ruta.extend(tramo[1:])
            cur = nxt
            pts.remove(nxt)
        tramo = camino_bfs(cur, m.mundo.refugio, transitable)
        if tramo is None:
            return []
        ruta.extend(tramo[1:])
        return ruta
    return planear


def _parametros_escenario(escenario: str) -> dict:
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario desconocido: {escenario!r}")
    par = ESCENARIOS[escenario]
    if escenario != "congelado" and not par.get("jugable") and (par["ruido"] is None or par["p_detectar"] is None):
        raise ValueError(f"escenario {escenario} pendiente de ARX-28a (ruido y p_detectar sin fijar)")
    return par


def _bateria_referencia(semilla: int, par: dict) -> float:
    """ARX-92c (criterio §12): batería = ⌈L_ref × COSTO × (1 + margen)⌉ + MARGEN_ENERGIA; L_ref = ruta voraz sin riesgo."""
    import math
    from genetico import COSTO_BATERIA_PASO
    from juego.partida import Partida, FILAS_BASE, COLUMNAS_BASE
    # batería ilimitada en la sonda: la ruta de referencia debe visitar todos los sitios (si no, _planear la descarta)
    sonda = Partida(semilla=semilla, nivel=par["nivel"], filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False,
                    n_sitios=par["n_sitios"], bateria=1e6)
    m = sonda.mision
    m.riesgo = np.zeros_like(m.riesgo)
    m.usar_rna = False
    m.usar_difuso = False
    m._optimizar_ag = _orden_voraz(m)
    m.objetivos = []
    m._planear()
    assert all(c in m.ruta for c in sonda.mundo.sitios), "la referencia debe pasar por todos los sitios"
    largo_ref = len(m.ruta) - 1
    from integracion import MARGEN_ENERGIA
    return float(math.ceil(largo_ref * COSTO_BATERIA_PASO * (1 + par["margen_bateria"])) + MARGEN_ENERGIA)


def partida_variante(semilla: int, variante: str, escenario: str = "congelado"):
    """Partida de la capa de juego con el escenario y, después, la variante aplicados antes de empezar."""
    from juego.partida import Partida
    par = _parametros_escenario(escenario)
    if variante not in VARIANTES and variante not in par.get("variantes", ()):
        raise ValueError(f"variante desconocida: {variante!r}")
    from juego.partida import FILAS_BASE, COLUMNAS_BASE
    if par.get("jugable"):
        return _partida_jugable(semilla, variante, par)
    if "n_sitios" in par:
        p = Partida(semilla=semilla, nivel=par["nivel"], filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False,
                    n_sitios=par["n_sitios"], bateria=_bateria_referencia(semilla, par))
    else:
        p = Partida(semilla=semilla, nivel=par["nivel"], filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=False)   # 20x30, sin redibujar el mapa
    m = p.mision
    p.fisica_velocidad = bool(par.get("fisica_velocidad", False))      # ARX-28c: resbalón por velocidad, solo el exigente
    if par["ruido"] is not None or par["p_detectar"] is not None or par.get("prob_fallo") is not None:
        # El escenario se aplica sobre la instancia y se replanifica con el mapa estimado nuevo
        if par["ruido"] is not None:
            m.sensor.ruido = par["ruido"]
        if par.get("prob_fallo") is not None:
            m.sensor.prob_fallo = par["prob_fallo"]
        if par["p_detectar"] is not None:
            m.riesgo = mapa_estimado(m.mundo, m.rng, p_detectar=par["p_detectar"])
        m.objetivos = []
        m._planear()
    if variante == "sin_rna":
        m.usar_rna = False
    elif variante == "sin_difuso":
        m.usar_difuso = False
    elif variante == "sin_ag_vecino":
        # Partida() ya planificó con el AG al construirse: se sustituye el optimizador y se replanifica
        m._optimizar_ag = _orden_voraz(m)
        m.objetivos = []
        m._planear()
    elif variante == "sin_ag_2opt":
        # ARX-92c: línea base de mejora local. Orden del vecino más cercano mejorado por 2-opt; RNA y difuso activos
        m._optimizar_ag = _orden_2opt(m)
        m.objetivos = []
        m._planear()
    elif variante == "sin_ag_mas_corta":
        # ARX-92d: el envoltorio de orden con pesos solo de distancia elige la permutación de menor largo
        from juego.partida import _ag_con_todos_los_sitios
        m._optimizar_ag = _ag_con_todos_los_sitios(m, _orden_voraz(m), pesos={"ciencia": 0, "distancia": 5, "energia": 0, "riesgo": 0, "tiempo": 0})
        m.objetivos = []
        m._planear()
    elif variante == "ruta_corta":
        m.usar_rna = False
        m.usar_difuso = False
        m.riesgo = np.zeros_like(m.riesgo)          # sin riesgos: el plan solo busca la ruta más corta
        m._optimizar_ag = _orden_voraz(m)
        m.objetivos = []
        m._planear()
    elif variante == "ag_puro":
        # No mide el AG: el envoltorio de Partida elige la permutación más corta; se redefine en ARX-92 (ev3-d71).
        m.usar_rna = False
        m.usar_difuso = False
        _congelar_riesgo(m)
    return p


def _partida_jugable(semilla: int, variante: str, par: dict):
    """R23: partida jugable (garantia=True, plan restringido) con la variante aplicada antes de empezar."""
    from juego.partida import FILAS_BASE, COLUMNAS_BASE, Partida, _ag_restringido
    p = Partida(semilla=semilla, nivel=par["nivel"], filas=FILAS_BASE, columnas=COLUMNAS_BASE, garantia=True,
                planeta=par["planeta"], n_sitios=par.get("n_sitios"), difuso_evolucionado=(variante != "difuso_base"))
    m = p.mision
    if variante == "sin_rna":
        m.usar_rna = False
    elif variante == "sin_difuso":
        m.usar_difuso = False
    elif variante.startswith("sin_ag_"):
        heuristica = {"sin_ag_vecino": "vecino", "sin_ag_2opt": "2opt", "sin_ag_ventanas": "ventanas"}[variante]
        m._optimizar_ag = _ag_restringido(p, heuristica=heuristica, anotar=p._avisar)
        m.objetivos = []
        p._wp = []
        p._plan_inicial_pendiente = False
        m._planear()
    elif variante not in ("hibrido", "difuso_base"):
        raise ValueError(f"variante desconocida: {variante!r}")
    return p


def _congelar_riesgo(m: Mision):
    """Mapa de riesgo fijo: tras cada paso_mision se restaura el snapshot tomado al empezar (ver docstring, ag_puro)."""
    snapshot = m.riesgo.copy()
    paso_original = m.paso_mision

    def paso_con_riesgo_fijo():
        try:
            return paso_original()
        finally:
            m.riesgo[...] = snapshot
    m.paso_mision = paso_con_riesgo_fijo


def correr(semilla: int, variante: str, escenario: str = "congelado") -> dict:
    """Una partida completa de una variante con una semilla."""
    p = partida_variante(semilla, variante, escenario)
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    fila = {"semilla": semilla, "variante": variante, "estado": p.estado, "exito": p.estado == "EXITO",
            "pasos": pasos, "colisiones": int(p.mision.colisiones),
            "bateria_final": round(float(p.rover.bateria), 2),
            "sitios_visitados": len(p.mision.visitados)}
    if p.plan_activo:      # R23: ciencia recogida (valor por la calidad de la ventana) y puntaje de la partida jugable
        fila["ciencia"] = p.ciencia()["fraccion"]
        fila["puntaje"] = p.puntaje()         # R23b: el único puntaje (juego/puntaje.py), el mismo de la partida, la API y los récords
        fila["recargas"] = int(p.recargas_hechas)
    return fila


def _resumen(valores) -> dict:
    v = np.asarray(valores, dtype=float)
    q1, q3 = np.percentile(v, [25, 75])
    return {"media": round(float(v.mean()), 3), "mediana": round(float(np.median(v)), 3),
            "desviacion": round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 3),
            "rango_intercuartil": round(float(q3 - q1), 3)}


def _wilson(k: int, n: int, z: float = 1.96) -> list:
    """Intervalo de Wilson del 95 % para una proporción, en % (éxitos k de n)."""
    if n == 0:
        return [0.0, 100.0]
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    mitad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(100 * max(0.0, centro - mitad), 1), round(100 * min(1.0, centro + mitad), 1)]


def _error_estandar(valores) -> float:
    v = np.asarray(valores, dtype=float)
    return round(float(np.std(v, ddof=1) / np.sqrt(len(v))), 4) if len(v) > 1 else 0.0


def _diferencia(x, y) -> dict:
    """Media de (variante − híbrido) sobre pares (misma semilla), su error estándar y si |z| ≥ 1,96 (95 %): distinguible del ruido."""
    d = np.asarray(y, dtype=float) - np.asarray(x, dtype=float)
    n = len(d)
    media = float(d.mean()) if n else 0.0
    ee = float(np.std(d, ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    z = media / ee if ee > 0 else (0.0 if media == 0 else float("inf") * np.sign(media))
    return {"n": int(n), "diferencia": round(media, 4), "error_estandar": round(ee, 4),
            "z": round(float(z), 2) if np.isfinite(z) else None, "distinguible_del_ruido": bool(abs(z) >= 1.96)}


def _diferencias_pareadas(hib: dict, var: dict) -> dict:
    """Diferencias (variante − híbrido) por semilla. Éxito en puntos de porcentaje; ciencia y puntaje en todas las semillas;
    pasos solo en las semillas que ganan las dos (una partida perdida termina antes y sus pasos no son comparables)."""
    comunes = sorted(set(hib) & set(var))
    exito = _diferencia([100.0 * hib[s]["exito"] for s in comunes], [100.0 * var[s]["exito"] for s in comunes])
    ambas = [s for s in comunes if hib[s]["exito"] and var[s]["exito"]]
    return {"exito_pp": exito,
            "ciencia": _diferencia([hib[s]["ciencia"] for s in comunes], [var[s]["ciencia"] for s in comunes]),
            "puntaje": _diferencia([hib[s]["puntaje"] for s in comunes], [var[s]["puntaje"] for s in comunes]),
            "pasos_si_ganan_las_dos": _diferencia([hib[s]["pasos"] for s in ambas], [var[s]["pasos"] for s in ambas]),
            "nota": "variante − híbrido, mismas semillas; «distinguible_del_ruido» = |diferencia ÷ error estándar| ≥ 1,96"}


def comparar(semillas, escenario: str = "congelado") -> dict:
    """Ejecuta todas las variantes con las mismas semillas y resume cada una."""
    par = _parametros_escenario(escenario)          # falla pronto si el escenario no existe o está pendiente
    variantes = tuple(par.get("variantes", VARIANTES))
    semillas = [int(s) for s in semillas]
    filas = [correr(s, v, escenario) for v in variantes for s in semillas]
    politicas = {}
    for v in variantes:
        grupo = [f for f in filas if f["variante"] == v]
        politicas[v] = {
            "exitos": sum(f["exito"] for f in grupo),
            "n": len(grupo),
            "tasa_exito": round(100.0 * sum(f["exito"] for f in grupo) / len(grupo), 1),
            "pasos": _resumen([f["pasos"] for f in grupo]),
            "colisiones": _resumen([f["colisiones"] for f in grupo]),
            "bateria_final": _resumen([f["bateria_final"] for f in grupo]),
            "sitios_visitados": _resumen([f["sitios_visitados"] for f in grupo]),
        }
        if "ciencia" in grupo[0]:
            politicas[v]["ic95_exito"] = _wilson(sum(f["exito"] for f in grupo), len(grupo))
            for clave in ("ciencia", "puntaje", "recargas"):
                politicas[v][clave] = {**_resumen([f[clave] for f in grupo]),
                                       "error_estandar": _error_estandar([f[clave] for f in grupo])}
            politicas[v]["pasos"]["error_estandar"] = _error_estandar([f["pasos"] for f in grupo])   # R23b
    if "hibrido" in politicas and "ciencia" in filas[0]:
        for v in variantes:      # R23b: diferencia contra el híbrido con las mismas semillas y si se distingue del ruido
            if v != "hibrido":
                politicas[v]["frente_al_hibrido"] = _diferencias_pareadas(
                    {f["semilla"]: f for f in filas if f["variante"] == "hibrido"},
                    {f["semilla"]: f for f in filas if f["variante"] == v})
    return {"escenario": escenario, "semillas": semillas, "variantes": politicas, "filas": filas,
            "nota": "Arnés: capa de juego (juego/partida.py), misma semilla por variante. Sin atribución causal fuera "
                    "de estas condiciones (§14). Los intentos a barranco no se miden en el híbrido."}


# ---------- traza de divergencias por técnica (ARX-28b) ----------
TECNICA = {"sin_rna": "RNA", "sin_difuso": "difuso", "sin_ag_vecino": "AG", "sin_ag_mas_corta": "AG"}


def _filas_por_paso(p) -> dict:
    """Filas de la bitácora agrupadas por paso, como tuplas comparables (posición, acción, velocidad, motivos)."""
    por_paso = {}
    for f in p.mision.log.filas:
        por_paso.setdefault(f["paso"], []).append(f)
    return por_paso


def _correr_traza(semilla: int, variante: str, escenario: str):
    p = partida_variante(semilla, variante, escenario)
    orden = [c for c in p.mision.objetivos if c in p.mundo.sitios]
    pasos = 0
    while p.estado not in ESTADOS_TERMINALES and pasos < MAX_PASOS:
        p.avanzar_ia()
        pasos += 1
    return p, orden


def _firma(filas) -> tuple:
    return tuple((f["posicion"], f["accion"], f["velocidad"], f["motivos"]) for f in filas)


def _motivo_y_cambio(variante, fh, fv):
    """Motivo (en el híbrido, que es quien tiene la técnica) y qué cambió, entre dos filas del mismo paso."""
    mh = ";".join(f["motivos"] for f in fh)
    cambios = []
    if [f["accion"] for f in fh] != [f["accion"] for f in fv]:
        cambios.append("decision")
    if [f["velocidad"] for f in fh] != [f["velocidad"] for f in fv]:
        cambios.append("velocidad")
    if [f["posicion"] for f in fh] != [f["posicion"] for f in fv]:
        cambios.append("ruta")
    if variante == "sin_rna":
        vetos = [m for m in mh.split(";") if m.startswith("V-RNA-")]
        motivo = ";".join(vetos) if vetos else "RNA (probabilidades distintas; motivos: " + (mh or "-") + ")"
    elif variante == "sin_difuso":
        reglas = ";".join(f["reglas"] for f in fh if f["reglas"])
        motivo = "regla difusa: " + (reglas or "-")
    else:
        motivo = "ruta del AG frente a vecino más cercano"
    return motivo, "+".join(cambios) or "otros_motivos"


def trazar_divergencias(semillas, escenario: str = "exigente") -> list:
    """Comparación paso a paso del híbrido contra cada variante con la misma semilla.

    Una fila por paso en que difiere lo registrado (posición, acción, velocidad o motivos). `origen`:
    - "directa": la PRIMERA divergencia de cada (semilla, variante) que altera decisión, velocidad o ruta, con el
      mismo estado previo (misma posición y batería al empezar el paso), por lo que la causa la técnica en ese paso
      (o, en el AG, el orden de sitios del plan);
    - "directa_codigo": divergencia con el mismo estado previo que solo cambia el código de motivo y aparece antes de
      la directa (o si no hay directa); se cuenta aparte y no cuenta como directa;
    - "consecuencia": el resto (toda divergencia posterior a la directa o con estado previo distinto).
    Se omiten los pasos en que una de las dos partidas ya terminó y no tiene fila (artefacto de fin de partida).
    Con sin_ag_vecino o sin_ag_mas_corta se añade, en paso 0, la fila de orden de sitios si el plan inicial difiere.
    """
    filas = []
    for s in semillas:
        ph, orden_h = _correr_traza(s, "hibrido", escenario)
        fh = _filas_por_paso(ph)
        for var in ("sin_rna", "sin_difuso", "sin_ag_vecino", "sin_ag_mas_corta"):
            pv, orden_v = _correr_traza(s, var, escenario)
            fv = _filas_por_paso(pv)
            if var.startswith("sin_ag") and orden_h != orden_v:
                filas.append({"semilla": s, "variante": var, "tecnica": "AG", "paso": 0, "celda": str(ph.mundo.inicio),
                              "origen": "directa", "motivo": "ruta del AG frente a vecino más cercano",
                              "cambio": "ruta", "detalle": f"orden AG {orden_h} / orden voraz {orden_v}"})
            previa_h = previa_v = None
            hubo_directa = bool(filas) and filas[-1]["semilla"] == s and filas[-1]["variante"] == var
            for paso in sorted(set(fh) | set(fv)):
                a, b = fh.get(paso, []), fv.get(paso, [])
                igual_previo = previa_h == previa_v
                if a and b and _firma(a) != _firma(b):
                    motivo, cambio = _motivo_y_cambio(var, a, b)
                    celda = (a or b)[-1]["posicion"]
                    if igual_previo and not hubo_directa:
                        origen = "directa_codigo" if cambio == "otros_motivos" else "directa"
                    else:
                        origen = "consecuencia"
                    filas.append({"semilla": s, "variante": var, "tecnica": TECNICA[var], "paso": paso, "celda": celda,
                                  "origen": origen,
                                  "motivo": motivo,
                                  "cambio": cambio,
                                  "detalle": f"hibrido {_firma(a)} / {var} {_firma(b)}"})
                    hubo_directa = hubo_directa or origen == "directa"
                previa_h = (a[-1]["posicion"], a[-1]["bateria"]) if a else previa_h
                previa_v = (b[-1]["posicion"], b[-1]["bateria"]) if b else previa_v
    return filas
