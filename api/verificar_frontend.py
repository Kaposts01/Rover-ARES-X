"""Verificación del frontend 3D (ARX-04) con Playwright: consola limpia en modo manual y captura.

Uso (con la API levantada en otro proceso):
    python -m uvicorn api.servidor:app --port 8765
    python api/verificar_frontend.py --url http://127.0.0.1:8765/ --salida docs/capturas
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright


def verificar(url: str, carpeta_salida: str) -> dict:
    os.makedirs(carpeta_salida, exist_ok=True)
    errores_consola = []
    errores_pagina = []
    solicitudes_fallidas = []

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(headless=True, args=["--use-gl=swiftshader", "--enable-webgl"])
        pagina = navegador.new_page(viewport={"width": 1280, "height": 720})
        pagina.on("console", lambda msg: errores_consola.append(msg.text) if msg.type == "error" else None)
        pagina.on("pageerror", lambda exc: errores_pagina.append(str(exc)))
        pagina.on("requestfailed", lambda req: solicitudes_fallidas.append(req.url))

        pagina.goto(url, wait_until="networkidle")
        pagina.click("#iniciar")          # menú de inicio (ARX-14)
        pagina.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
        pagina.wait_for_function("document.getElementById('h-estado').textContent !== '-'", timeout=20000)

        estado_inicial = pagina.inner_text("#h-estado")
        pagina.keyboard.press("ArrowUp")
        pagina.wait_for_timeout(600)
        pagina.click("#pad button[data-r='E']")
        pagina.wait_for_timeout(600)
        pagina.keyboard.press("9")
        pagina.wait_for_timeout(600)
        mensaje = pagina.inner_text("#mensaje")
        # Movimiento rechazado: el rover pega contra el borde izquierdo del mapa
        for _ in range(3):
            pagina.keyboard.press("ArrowLeft")
            pagina.wait_for_timeout(400)
        mensaje_rechazo = pagina.inner_text("#mensaje")

        ruta_captura = os.path.join(carpeta_salida, "escena_manual.png")
        pagina.screenshot(path=ruta_captura)
        navegador.close()

    return {
        "estado_inicial": estado_inicial,
        "mensaje_final": mensaje,
        "mensaje_rechazo": mensaje_rechazo,
        "errores_consola": errores_consola,
        "errores_pagina": errores_pagina,
        "solicitudes_fallidas": solicitudes_fallidas,
        "captura": ruta_captura,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/")
    parser.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "capturas"))
    args = parser.parse_args()
    resultado = verificar(args.url, args.salida)
    for clave, valor in resultado.items():
        print(f"{clave}: {valor}")
    limpia = not resultado["errores_consola"] and not resultado["errores_pagina"]
    print("CONSOLA_LIMPIA:", limpia)
    sys.exit(0 if limpia else 1)
