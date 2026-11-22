"""Construye el notebook único de entrega (ev3-d03) a partir de los módulos de ares_x/.

Uso (desde ares_x/):  python construir_notebook.py
Genera ARES_X_entregable.ipynb, sin archivos locales ni imports del proyecto.
"""
import re
from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parent
MODULOS = ["simulador.py", "rna.py", "difuso.py", "genetico.py", "integracion.py", "intervencion.py"]
IMPORT_LOCAL = re.compile(r"^from (simulador|rna|difuso|genetico|integracion|intervencion) import")


def quitar_imports_locales(texto: str) -> str:
    """Quita los imports entre módulos del proyecto (incluidos los de varias líneas)."""
    salida, saltando = [], False
    for linea in texto.splitlines():
        if saltando:
            if ")" in linea:
                saltando = False
            continue
        if IMPORT_LOCAL.match(linea):
            if "(" in linea and ")" not in linea:
                saltando = True
            continue
        salida.append(linea)
    return "\n".join(salida)


def codigo_modulo(nombre: str) -> str:
    texto = (RAIZ / nombre).read_text(encoding="utf-8")
    # El docstring del módulo pasa a ser comentario de la celda, para no duplicar encabezados
    return f"# ----- {nombre} -----\n" + quitar_imports_locales(texto)


CELDA_INTRO = """# ARES-X: rover autónomo con IA híbrida (RNA + lógica difusa + algoritmo genético)

**Entrega individual · Evaluación ev3 · Plazo: mediodía del 10 de noviembre (recorte fuerte).**

**Alcance de esta entrega:**
- Mapa de Marte reproducible por semilla, con obstáculos, barrancos y sitios científicos.
- **RNA** (MLP 32-16) que clasifica libre, obstáculo o barranco con partición por mapas.
- **Lógica difusa** Mamdani con 9 reglas, para la velocidad.
- **Algoritmo genético** con K puntos de paso, para la ruta, sobre el mapa estimado (ev3-d01, ev3-d02).
- **Supervisor** de seguridad con vetos y códigos de motivo, y replanteo con BFS (ev3-d07, opción B).
- **Experimento** de 20 semillas con dos ablaciones (sin RNA, sin difuso).

**Naturaleza:** simulación ficticia con parámetros de referencia. Todo valor sin fuente se marca como *supuesto de simulación*.

**Entorno:** Python 3.11 o superior en CPU, en local (Windows o Linux). No requiere claves ni archivos externos.

**Qué no incluye (recorte):** demás planetas en modo sonda, eventos de sismo y tormenta, interfaz de ipywidgets completa.
"""

CELDA_INSTALACION = """# Dependencias. Ejecutar solo si falta alguna (ver requirements.txt).
# !pip install -q scikit-learn matplotlib pandas nbformat
"""

CELDA_EXPERIMENTO_INTRO = """## 5. Experimento: 20 semillas, híbrido frente a ablaciones

Cada semilla genera un mapa distinto. Se comparan tres variantes con la misma misión:
- **sin RNA** (ablación): la RNA se quita del ciclo.
- **sin difuso** (ablación): la velocidad queda fija en 0,5.

Se reportan éxito, colisiones, barrancos pisados, sitios visitados, pasos y batería, con media, mediana y dispersión.
"""

CELDA_EXPERIMENTO = """import pandas as pd

SEMILLAS = range(20)

VARIANTES = {
    "híbrido": {},
    "sin RNA (ablación)": {"usar_rna": False},
    "sin difuso (ablación)": {"usar_difuso": False},
}

filas = []
for nombre, opciones in VARIANTES.items():
    for s in SEMILLAS:
        mundo = generar_mundo(semilla=s, n_obstaculos=20, n_barrancos=4, n_sitios=3)
        r = Mision(mundo, semilla=s, **opciones).ejecutar(max_pasos=400)
        filas.append({"variante": nombre, "semilla": s, **r})

tabla = pd.DataFrame(filas)
tabla["exito"] = tabla["estado"].eq("EXITO").astype(int)
tabla_resumen = tabla.groupby("variante").agg(
    exito_pct=("exito", lambda x: round(100 * x.mean(), 1)),
    colisiones=("colisiones", "sum"),
    barrancos_pisados=("barrancos_pisados", "sum"),
    sitios_media=("sitios_visitados", "mean"),
    pasos_mediana=("pasos", "median"),
    pasos_desv=("pasos", "std"),
    bateria_media=("bateria_final", "mean"),
)
tabla_resumen.round(2)
"""

CELDA_DETALLE = """# Detalle por semilla del sistema híbrido
tabla[tabla["variante"] == "híbrido"][["semilla", "estado", "pasos", "sitios_visitados",
                                      "bateria_final", "vetos", "replanes", "colisiones"]]
"""

CELDA_INTERVENCION_INTRO = """## 5b. Prueba causal: intervención en la RNA y en el difuso (ev3-d32 A)

Se fuerza la salida de la RNA (barranco, libre) y la del difuso (velocidad 0 y velocidad 1). Para cada semilla se compara la misión base con la intervenida, con la misma semilla. El primer paso donde cambia la acción o la velocidad mide el efecto causal.
"""

CELDA_INTERVENCION = """tabla_intervencion = correr(range(20))
resumen(tabla_intervencion)
"""

CELDA_DEMO = """## 6. Una misión paso a paso (bitácora)

Se ejecuta una misión y se muestra su bitácora. Cada fila es un paso del pseudociclo.
"""

CELDA_DEMO_CODIGO = """mision = Mision(generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3), semilla=11)
mision.ejecutar(max_pasos=400)
bitacora = mision.log.a_dataframe()
print("Resumen:", mision.resumen())
bitacora[["paso", "estado", "posicion", "bateria", "accion", "velocidad", "p_barranco", "motivos"]].head(15)
"""

CELDA_EXPORTAR = """# Exportación de la misión: trazas en CSV y configuración con resultados en JSON
import json

bitacora.to_csv("mision_traza.csv", index=False)
with open("mision_resumen.json", "w", encoding="utf-8") as f:
    json.dump({"semilla": 11, "planeta": "Marte", "config": {"n_obstaculos": 20, "n_barrancos": 4,
               "n_sitios": 3, "bateria_inicial": 100.0}, "resultado": mision.resumen(),
               "supuesto": "parámetros de simulación ficticios, no especificaciones NASA"},
              f, ensure_ascii=False, indent=2)
print("Exportado: mision_traza.csv y mision_resumen.json")
"""

CELDA_FIGURAS = """# Figuras 2D del informe (matriz de confusión y ablación). Se muestran solo si ya fueron generadas
# con scripts/generar_figuras.py; esta celda no las calcula.
from pathlib import Path
from IPython.display import Image, display

# La carpeta se busca desde el directorio actual (ares_x/ o su carpeta madre); si falta, solo se avisa.
_carpeta = next((c for c in (Path("docs/figuras"), Path("ares_x/docs/figuras")) if c.is_dir()), None)
if _carpeta is None:
    print("Figuras no encontradas: ejecutar el notebook desde ares_x/ y generarlas con scripts/generar_figuras.py")
else:
    for _nombre in ("matriz_confusion.png", "ablacion.png"):
        if (_carpeta / _nombre).exists():
            display(Image(filename=str(_carpeta / _nombre)))
        else:
            print("Figura no generada:", _nombre)
"""

CELDA_CONCLUSIONES = """## 7. Resultados, limitaciones y conclusiones

**Experimento (20 semillas, mapas de Marte, movimiento en 8 direcciones)**
- Híbrido: 100 % de éxito, 0 colisiones, 0 barrancos pisados, 1,7 sitios de media, mediana de 39,5 pasos y batería media de 61,1 %.
- Ablaciones (sin RNA, sin difuso): mismas cifras. Con los sensores activos, la RNA y el difuso no cambian el resultado final en este escenario.
- RNA en prueba (modelo del notebook: 60 mapas, 400 muestras por mapa): macro-F1 0,928 y recall de barrancos 0,943 (33 de 35). La línea base por clase mayoritaria es 0,927.

**Prueba causal (intervención forzada)**
- RNA forzada a barranco: la decisión cambia en 20 de 20 semillas desde el paso 1; el éxito cae a 0 % porque el supervisor veta sin parar.
- RNA forzada a libre: no cambia ninguna decisión (0 de 20).
- Velocidad del difuso forzada a 0: la decisión cambia en 20 de 20; el éxito cae a 0 %.
- Velocidad del difuso forzada a 1: la decisión cambia en 20 de 20; el éxito sigue en 100 %.

**Combate**
- En modo automático, con dos drones activos, la semilla 11 llega al refugio en 52 pasos, sin colisiones.

**Limitaciones conocidas**
- Falso positivo del sensor: con ruido, una celda libre puede quedar marcada como obstáculo y el plan puede dar SIN_RUTA aunque el mapa real tenga camino.
- El plan omite sitios científicos por energía: se visitan 1,7 de 3 de media.
- El supervisor está congelado y no conoce a los drones: la decisión de combate vive en la capa de la API.
- Los modos rna, difuso y ag muestran sus paneles, pero el paso lo da siempre el pipeline completo.

**Conclusión**
Las tres técnicas están implementadas, probadas por separado y conectadas en el ciclo de decisión con supervisor de seguridad. La evidencia principal es el experimento de 20 semillas y la prueba causal, que muestran que alterar la salida de la RNA o del difuso cambia la decisión, aunque en este escenario el resultado final depende sobre todo del sensor y del supervisor.
"""


def construir():
    nb = nbf.v4.new_notebook()
    celdas = [
        nbf.v4.new_markdown_cell(CELDA_INTRO),
        nbf.v4.new_code_cell(CELDA_INSTALACION),
        nbf.v4.new_markdown_cell("## 1. Módulos: simulador, RNA, difuso, AG y supervisor\n\n"
                                 "Cada celda es un módulo del proyecto, unido en un solo notebook."),
    ]
    for modulo in MODULOS:
        celdas.append(nbf.v4.new_code_cell(codigo_modulo(modulo)))
    celdas += [
        nbf.v4.new_markdown_cell("## 2. Entrenamiento de la RNA\n\nLa RNA se entrena con mapas separados por semilla. Se reporta macro-F1 y recall de barrancos en prueba."),
        nbf.v4.new_code_cell(
            "tr, va, te = particion_por_mapas(total_mapas=60)\n"
            "X_tr, y_tr = generar_dataset(tr, muestras_por_mapa=400, refuerzo_barranco=REFUERZO_BARRANCO_POR_MAPA)\n"
            "X_te, y_te = generar_dataset(te, muestras_por_mapa=400)\n"
            "rna_final = NeuralPerception(semilla=42).entrenar(X_tr, y_tr)\n"
            "res = rna_final.evaluar(X_te, y_te)\n"
            "print(f'macro-F1 = {res.macro_f1:.3f}  recall barrancos = {res.recall_barranco:.3f}')\n"
            "print(f'línea base (clase mayoritaria) = {res.precision_base:.3f}  ECE = {res.error_calibracion:.3f}')\n"
            "res.matriz_confusion"
        ),
        nbf.v4.new_markdown_cell("## 3. Lógica difusa\n\nEjemplos de inferencia con reglas activadas."),
        nbf.v4.new_code_cell(
            "ctrl = FuzzyController()\n"
            "for caso in [dict(distancia=1, bateria=90, inclinacion=5), dict(distancia=18, bateria=90, inclinacion=2)]:\n"
            "    r = ctrl.inferir(**caso)\n"
            "    print(caso, '-> velocidad', round(r.velocidad, 3), [x[0] for x in r.reglas_activadas])"
        ),
        nbf.v4.new_markdown_cell("## 4. Algoritmo genético\n\nPlanificación de una ruta sobre el mapa estimado, con desglose del fitness."),
        nbf.v4.new_code_cell(
            "mundo = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)\n"
            "riesgo = mapa_estimado(mundo, np.random.default_rng(11))\n"
            "res_ag = GeneticPlanner(mundo, riesgo, bateria=100, k_puntos=3, semilla=11).optimizar()\n"
            "print('fitness', round(res_ag.mejor_desglose.fitness, 3), 'pasos', res_ag.mejor_desglose.ruta_pasos)\n"
            "res_ag.mejor_desglose"
        ),
        nbf.v4.new_markdown_cell(CELDA_EXPERIMENTO_INTRO),
        nbf.v4.new_code_cell(CELDA_EXPERIMENTO),
        nbf.v4.new_code_cell(CELDA_DETALLE),
        nbf.v4.new_markdown_cell(CELDA_INTERVENCION_INTRO),
        nbf.v4.new_code_cell(CELDA_INTERVENCION),
        nbf.v4.new_markdown_cell(CELDA_DEMO),
        nbf.v4.new_code_cell(CELDA_DEMO_CODIGO),
        nbf.v4.new_code_cell(CELDA_EXPORTAR),
        nbf.v4.new_code_cell(CELDA_FIGURAS),
        nbf.v4.new_markdown_cell(CELDA_CONCLUSIONES),
    ]
    nb["cells"] = celdas
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    salida = RAIZ / "ARES_X_entregable.ipynb"
    nbf.write(nb, salida)
    return salida


if __name__ == "__main__":
    print("Notebook generado:", construir())
