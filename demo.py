"""Demo manual de ARES-X: muestra cada módulo en la terminal.

Uso (desde ares_x/):  python demo.py
"""
import numpy as np

from difuso import FuzzyController
from genetico import GeneticPlanner, mapa_estimado
from rna import REFUERZO_BARRANCO_POR_MAPA, NeuralPerception, generar_dataset, particion_por_mapas
from simulador import (PERFILES, SensorSuite, generar_mundo, paso_fisico, Rover,
                       validar_compatibilidad)


def titulo(texto):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def demo_simulador():
    titulo("1. SIMULADOR (Fase 1)")
    mundo = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    print(f"Mapa {mundo.forma}, semilla {mundo.semilla}, inicio {mundo.inicio}, refugio {mundo.refugio}")
    print(f"Sitios científicos: {mundo.sitios}")

    for planeta, modo in [("Marte", "rover"), ("Júpiter", "rover")]:
        try:
            validar_compatibilidad(planeta, modo)
            print(f"{planeta} + {modo}: OK")
        except ValueError as e:
            print(f"{planeta} + {modo}: BLOQUEADO -> {e}")

    sensor = SensorSuite(rng=np.random.default_rng(0), ruido=0.1)
    print("Lectura de sensores en el inicio:", sensor.leer(mundo, mundo.inicio, "N"))

    rover = Rover(posicion=mundo.inicio, bateria=100.0)
    movidos = sum(paso_fisico(mundo, rover, "N") for _ in range(3))
    print(f"Tres pasos al norte: {movidos} movidos, batería {rover.bateria:.1f}%")


def demo_difuso():
    titulo("2. LÓGICA DIFUSA (Fase 3)")
    ctrl = FuzzyController()
    casos = [
        ("Obstáculo a 1 m", dict(distancia=1, bateria=90, inclinacion=5)),
        ("Camino libre, batería alta", dict(distancia=18, bateria=90, inclinacion=2)),
        ("Batería crítica", dict(distancia=18, bateria=5, inclinacion=2)),
        ("Caso con varias reglas", dict(distancia=8, bateria=30, inclinacion=25)),
    ]
    for nombre, entrada in casos:
        r = ctrl.inferir(**entrada)
        print(f"\n{nombre}: {entrada}")
        print(f"  velocidad = {r.velocidad:.3f}  (fallback: {r.fallback})")
        for rid, fuerza, motivo in r.reglas_activadas:
            print(f"  {rid} fuerza={fuerza:.2f}  {motivo}")


def demo_rna():
    titulo("3. RED NEURONAL (Fase 2)")
    print("Entrenando con mapas separados por semilla (puede tardar unos segundos)...")
    tr, va, te = particion_por_mapas(total_mapas=60)
    Xtr, ytr = generar_dataset(tr, muestras_por_mapa=400, refuerzo_barranco=REFUERZO_BARRANCO_POR_MAPA)
    Xte, yte = generar_dataset(te, muestras_por_mapa=400)
    rna = NeuralPerception(semilla=42).entrenar(Xtr, ytr)
    res = rna.evaluar(Xte, yte)
    print(f"Prueba: macro-F1 = {res.macro_f1:.3f}, recall barrancos = {res.recall_barranco:.3f}")
    print(f"Línea base (clase mayoritaria) = {res.precision_base:.3f}, ECE = {res.error_calibracion:.3f}")
    print("Matriz de confusión (filas = real; columnas = predicho; libre, obstáculo, barranco):")
    print(res.matriz_confusion)
    print("\nEjemplo de explicación para una lectura:")
    print(rna.explicar(Xte[0]))


def demo_genetico():
    titulo("4. ALGORITMO GENÉTICO (Fase 4)")
    mundo = generar_mundo(semilla=11, n_obstaculos=20, n_barrancos=4, n_sitios=3)
    riesgo = mapa_estimado(mundo, np.random.default_rng(11))
    gp = GeneticPlanner(mundo, riesgo, bateria=100, k_puntos=3, semilla=11)
    res = gp.optimizar()
    print("Evolución (mejor fitness por generación, primeras y últimas):")
    for h in res.historial[:3] + res.historial[-3:]:
        print(f"  gen {h['generacion']:2d}: mejor={h['mejor']:.3f} media={h['media']:.3f}")
    print("\nTres candidatos finales:")
    for i, (cromo, d) in enumerate(res.candidatos, 1):
        print(f"  {i}. fitness={d.fitness:.3f} ciencia={d.ciencia:.2f} pasos={d.ruta_pasos} "
              f"riesgo={d.riesgo:.2f} penalización={d.penalizacion:.2f}")
    print(f"\nRuta elegida ({len(res.mejor_ruta)} celdas): {res.mejor_ruta[:6]} ...")


if __name__ == "__main__":
    print("Planetas disponibles:", ", ".join(PERFILES))
    demo_simulador()
    demo_difuso()
    demo_genetico()
    demo_rna()
    print("\nDemo terminada.")
