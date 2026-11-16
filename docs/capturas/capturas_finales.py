"""Capturas finales de ARES-X para el informe y el video (ARX-49).

Regenera todas las vistas con Playwright. Requiere el servidor en marcha:
    python -m uvicorn api.servidor:app --port 8765

Uso (desde ares_x/):
    python docs/capturas/capturas_finales.py [--url http://127.0.0.1:8765/] [--salida docs/capturas/finales]

Solo toca docs/capturas. No usa el puerto 8000.
"""
import argparse
import os
import time

from playwright.sync_api import sync_playwright

VISTAS = [
    # (nombre, ancho, alto, acciones)
    ("01_asistente_marte", 1366, 768, "asistente"),
    ("02_partida_marte_1366", 1366, 768, "partida"),
    ("03_partida_marte_1920", 1920, 1080, "partida"),
    ("04_decision_ia_rna", 1366, 768, "rna"),
    ("05_laboratorio_genetico", 1366, 768, "lab:ag"),
    ("06_laboratorio_difuso_barrido", 1366, 768, "lab:difuso"),
    ("07_laboratorio_rna", 1366, 768, "lab:rna"),
    ("08_comparacion_politicas", 1366, 768, "lab:politicas"),
    ("09_jupiter_sonda", 1366, 768, "jupiter"),
    ("10_mercurio", 1366, 768, "mercurio"),
    ("11_automatico_continuo", 1366, 768, "automatico"),
    ("12_estados_demo", 1366, 768, "estados"),
    ("13_modo_cine", 1366, 768, "cine"),
    ("14_movil", 375, 812, "partida"),
    ("15_tablet", 768, 1024, "partida"),
]


def esperar_partida(pag):
    pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
    pag.wait_for_timeout(1500)


def preparar(pag, accion):
    """Lleva la página al estado de cada vista."""
    if accion == "asistente":
        return
    if accion.startswith("jupiter"):
        pag.evaluate("() => { document.getElementById('menu-planeta').value = 'Júpiter'; document.getElementById('menu-planeta').dispatchEvent(new Event('change')); document.getElementById('menu-usar-sonda').click(); }")
    elif accion.startswith("mercurio"):
        pag.evaluate("() => { document.getElementById('menu-planeta').value = 'Mercurio'; document.getElementById('menu-planeta').dispatchEvent(new Event('change')); }")
    pag.click("#iniciar")
    esperar_partida(pag)
    if accion == "rna":
        pag.select_option("#modo", "rna")
        pag.wait_for_timeout(600)   # la decisión ya está abierta por defecto en escritorio
    elif accion == "automatico":
        pag.select_option("#modo", "automatico")
        pag.wait_for_timeout(2000)
    elif accion == "estados":
        pass   # la demo de estados se activa por URL (?demo=estados), ver main()
    elif accion == "cine":
        pag.keyboard.press("h")
        pag.wait_for_timeout(500)
    elif accion.startswith("lab:"):
        pag.click("#abrir-laboratorio")
        pestana = {"ag": "Genético", "difuso": "Difuso", "rna": "RNA", "politicas": "Políticas"}[accion.split(":")[1]]
        pag.click(f".lab-tab:has-text('{pestana}')")
        pag.wait_for_timeout(800)
        if accion == "lab:ag":
            pag.click("#ag-ejecutar")
            pag.wait_for_function("document.getElementById('ag-estado').textContent.includes('generaciones')", timeout=240000)
        if accion == "lab:difuso":
            pag.click("#dif-barrido")
            pag.wait_for_timeout(1500)
        if accion == "lab:politicas":
            pag.click("#pol-cargar")
            pag.wait_for_timeout(1500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765/")
    ap.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "finales"))
    args = ap.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True, args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        for nombre, ancho, alto, accion in VISTAS:
            pag = nav.new_page(viewport={"width": ancho, "height": alto})
            url = args.url + ("?demo=estados" if accion == "estados" else "")
            pag.goto(url, wait_until="networkidle")
            pag.wait_for_timeout(800)
            preparar(pag, accion)
            pag.wait_for_timeout(1200)
            ruta = os.path.join(args.salida, f"{nombre}.png")
            pag.screenshot(path=ruta)
            print("OK", ruta)
            pag.close()
            time.sleep(0.5)
        nav.close()


if __name__ == "__main__":
    main()
