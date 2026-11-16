"""Verificación de ARX-06 en el navegador: drones visibles, disparo y consola limpia.

Uso (API levantada):  python -m uvicorn api.servidor:app --port 8765
                      python api/verificar_combate.py --url http://127.0.0.1:8765/ --salida docs/capturas
Guarda combate.png con un dron cerca y el destello de un disparo.
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
        pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)

        # Modo automático: avanzar hasta que algún dron esté en alerta o persecución (o ataque)
        pag.select_option("#modo", "automatico")
        pag.wait_for_timeout(300)
        visto = False
        for _ in range(60):
            pag.click("#paso")
            pag.wait_for_timeout(250)
            texto = pag.inner_text("#h-drones")
            if any(e in texto for e in ("alerta", "persecucion", "ataque")):
                visto = True
                break
            if pag.inner_text("#h-estado") in ("EXITO", "FRACASO", "SIN_RUTA", "MODO_SEGURO"):
                break
        res["dron_en_alerta_o_persecucion"] = visto
        res["drones_estado"] = pag.inner_text("#h-drones")

        # Disparo con la tecla Espacio: el rover dispara hacia donde mira
        pag.keyboard.press(" ")
        pag.wait_for_timeout(500)
        res["mensaje_disparo"] = pag.inner_text("#mensaje")
        res["cooldown_tras_disparo"] = pag.inner_text("#h-cooldown")
        abrir_decision(pag)
        pag.screenshot(path=os.path.join(carpeta, "combate.png"))
        nav.close()

    res["errores_consola"] = errores_consola
    res["errores_pagina"] = errores_pagina
    res["consola_limpia"] = not errores_consola and not errores_pagina
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765/")
    parser.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "capturas"))
    args = parser.parse_args()
    r = verificar(args.url, args.salida)
    for k, v in r.items():
        print(f"{k}: {v}")
    sys.exit(0 if r["consola_limpia"] else 1)
