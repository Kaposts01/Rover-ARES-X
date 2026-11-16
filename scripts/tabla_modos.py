"""Tabla de 20 semillas por modo de conducción (ARX-11). Genera docs/TABLA_MODOS.md y docs/tabla_modos.csv.

Uso (desde ares_x/):  python scripts/tabla_modos.py
"""
import csv
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from juego.conduccion import correr  # noqa: E402

SEMILLAS = range(1, 21)
CONFIGURACIONES = [("automatico", None), ("rna", True), ("rna", False), ("difuso", True), ("difuso", False),
                   ("ag", True), ("ag", False)]


def etiqueta(modo, veto):
    if modo == "automatico":
        return "automático (supervisor completo)"
    return f"{modo}, veto {'encendido' if veto else 'apagado'}"


def main():
    filas = []
    for modo, veto in CONFIGURACIONES:
        for s in SEMILLAS:
            filas.append(correr(s, modo, True if veto is None else veto))
    carpeta = os.path.join(RAIZ, "docs")
    with open(os.path.join(carpeta, "tabla_modos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    lineas = ["# Tabla de 20 semillas por modo de conducción (ARX-11)", "",
              "Semillas 1 a 20. Éxito = llega a EXITO. Colisiones = movimientos bloqueados por la física. "
              "Intentos a barranco = movimientos dirigidos a una celda de barranco (solo cuentan con el veto apagado, "
              "porque con el veto encendido no se intentan). Pasos = iteraciones hasta un estado terminal o 400.", "",
              "Arnés: capa de juego (`juego/partida.py`, semillas 1 a 20, sin combate ni eventos). No es el mismo "
              "arnés que el experimento del notebook (`Mision` directa, 100 % de éxito para el híbrido): las dos cifras "
              "no se mezclan. El automático falla en la semilla 15 (SIN_RUTA con los tres sitios visitados), un falso "
              "positivo del sensor que ya está documentado en el INFORME.", "",
              "| Configuración | Éxito | Colisiones (media) | Intentos a barranco (media) | Pasos (mediana) |",
              "|---|---|---|---|---|"]
    for modo, veto in CONFIGURACIONES:
        grupo = [r for r in filas if r["modo"] == modo and (veto is None or r["veto"] == veto)]
        exitos = sum(r["exito"] for r in grupo)
        col = sum(r["colisiones"] for r in grupo) / len(grupo)
        bar = sum(r["intentos_barranco"] for r in grupo) / len(grupo)
        pasos = sorted(r["pasos"] for r in grupo)
        med = pasos[len(pasos) // 2] if len(pasos) % 2 else (pasos[len(pasos) // 2 - 1] + pasos[len(pasos) // 2]) / 2
        lineas.append(f"| {etiqueta(modo, veto)} | {exitos}/20 | {col:.2f} | {bar:.2f} | {med:g} |")
    with open(os.path.join(carpeta, "TABLA_MODOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
