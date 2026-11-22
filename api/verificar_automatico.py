"""Verificación de ARX-05 en el navegador (Playwright): modo automático, criterio 2 e intervención.

Uso (con la API levantada en otro proceso):
    python -m uvicorn api.servidor:app --port 8765
    python api/verificar_automatico.py --url http://127.0.0.1:8765/ --salida docs/capturas

Comprueba:
- Semilla 11 en modo automático llega a EXITO desde la interfaz (criterio 2 en la UI).
- Sin errores de consola ni de página (criterio 10 en modo automático).
- Intervención activa: aparece el aviso, y el cambio de decisión se ve en los paneles.
Guarda automatico.png (fin de la misión) e intervencion.png (aviso y paneles con la intervención).
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright


def abrir_decision(pag):
    """Abre el panel de decisiones (plegado por defecto) para que la captura muestre los valores."""
    if "plegado" in (pag.get_attribute("#decision", "class") or ""):
        pag.click("#decision-toggle")
        pag.wait_for_timeout(300)


def _estado(pagina) -> str:
    return pagina.inner_text("#h-estado")


def verificar(url: str, carpeta: str) -> dict:
    os.makedirs(carpeta, exist_ok=True)
    errores_consola, errores_pagina = [], []
    res = {}

    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True, args=["--use-gl=swiftshader", "--enable-webgl"])
        pag = nav.new_page(viewport={"width": 1280, "height": 720})
        pag.on("console", lambda m: errores_consola.append(m.text) if m.type == "error" else None)
        pag.on("pageerror", lambda e: errores_pagina.append(str(e)))

        pag.goto(url, wait_until="networkidle")
        pag.click("#iniciar")          # menú de inicio (ARX-14)
        pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
        pag.wait_for_function("document.getElementById('h-estado').textContent !== '-'", timeout=20000)

        # 1) Criterio 2 en la UI: semilla 11, modo automático, reproducir hasta EXITO
        pag.select_option("#modo", "automatico")
        pag.wait_for_timeout(400)
        pag.select_option("#velocidad", "150")
        pag.click("#reproducir")
        pag.wait_for_function(
            "['EXITO','FRACASO','SIN_RUTA','MODO_SEGURO'].includes(document.getElementById('h-estado').textContent)",
            timeout=180000,
        )
        pag.click("#reproducir") if "Pausa" in pag.inner_text("#reproducir") else None
        res["estado_automatico_semilla_11"] = _estado(pag)
        res["mensaje_final"] = pag.inner_text("#mensaje")
        pag.wait_for_timeout(500)
        abrir_decision(pag)
        pag.screenshot(path=os.path.join(carpeta, "automatico.png"))

        # 2) Intervención: nueva partida semilla 11, forzar la RNA a barranco y dar pasos
        pag.fill("#semilla", "11")
        pag.click("#nueva")
        pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
        pag.select_option("#modo", "automatico")
        pag.select_option("#int-tecnica", "rna-barranco")
        pag.click("#int-aplicar")
        pag.wait_for_timeout(500)
        for _ in range(3):
            pag.click("#paso")
            pag.wait_for_timeout(400)
        res["aviso_intervencion_visible"] = pag.is_visible("#intervencion-aviso")
        res["aviso_texto"] = pag.inner_text("#intervencion-aviso")
        res["supervisor_accion"] = pag.inner_text("#sup-accion")
        res["supervisor_motivos"] = pag.inner_text("#sup-motivos")
        res["p_barranco_mostrada"] = pag.inner_text("#rna-barranco")
        abrir_decision(pag)
        pag.screenshot(path=os.path.join(carpeta, "intervencion.png"))
        nav.close()

    res["errores_consola"] = errores_consola
    res["errores_pagina"] = errores_pagina
    res["criterio_10_consola_limpia"] = not errores_consola and not errores_pagina
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/")
    parser.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "capturas"))
    args = parser.parse_args()
    resultado = verificar(args.url, args.salida)
    for clave, valor in resultado.items():
        print(f"{clave}: {valor}")
    sys.exit(0 if resultado["criterio_10_consola_limpia"] else 1)
