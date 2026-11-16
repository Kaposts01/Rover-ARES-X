"""Verificación visual del S6 (ARX-52, 54, 56, 60-65 y el solape del registro).

Uso (desde ares_x/, con el servidor en 8765 y SOLO con turno de navegador):
    python docs/capturas/s6_verificacion.py
Salida: docs/capturas/s6/*.png. Vista de 960x540. Ver S6_verificacion_visual.md.
"""
import os

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "s6")
os.makedirs(SALIDA, exist_ok=True)


def captura(pag, nombre):
    pag.screenshot(path=os.path.join(SALIDA, nombre))
    print("OK", nombre)


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
    pag = nav.new_page(viewport={"width": 960, "height": 540})
    pag.goto(URL, wait_until="networkidle")
    pag.wait_for_timeout(600)
    captura(pag, "s6_01_asistente.png")

    # ARX-52 y ARX-56: partida sin semilla (la elige el servidor)
    pag.click("#iniciar")
    pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=120000)
    pag.wait_for_timeout(1500)
    captura(pag, "s6_02_partida.png")

    # ARX-54: manual y recomendaciones
    pag.click("#det-rec summary")
    pag.click("#rec-consultar")
    pag.wait_for_timeout(2500)
    captura(pag, "s6_03_manual_recomendaciones.png")

    # ARX-62: cámara en seguimiento, mapa desde arriba y mapa completo
    pag.click("#ver-mapa")
    pag.wait_for_timeout(800)
    captura(pag, "s6_04_camara.png")
    pag.click("#mapa-completo")
    pag.wait_for_timeout(800)

    # ARX-63: registro con varios pasos
    for _ in range(12):
        pag.click("#paso")
        pag.wait_for_timeout(200)
    captura(pag, "s6_05_registro.png")

    # Solape: intervención activa con el registro visible
    pag.select_option("#int-tecnica", "rna-barranco")
    pag.click("#int-aplicar")
    pag.wait_for_timeout(800)
    captura(pag, "s6_06_intervencion.png")
    pag.select_option("#int-tecnica", "ninguna")
    pag.click("#int-aplicar")

    # ARX-61: pausa
    pag.keyboard.press("Escape")
    pag.wait_for_timeout(500)
    captura(pag, "s6_07_pausa.png")
    pag.keyboard.press("Escape")

    # ARX-60: carga al reiniciar desde la pausa
    pag.keyboard.press("Escape")
    pag.click("#pausa-reiniciar")
    pag.wait_for_timeout(900)
    captura(pag, "s6_08_carga.png")
    pag.wait_for_timeout(2500)

    # ARX-64: meta (forzada con un fin de misión simulado)
    pag.evaluate("() => { document.getElementById('meta').classList.remove('oculto'); }")
    pag.wait_for_timeout(300)
    captura(pag, "s6_09_meta.png")
    pag.evaluate("() => { document.getElementById('meta').classList.add('oculto'); }")

    nav.close()
print("Listo. Recordar: cerrar el navegador y comprobar 0 procesos headless.")
