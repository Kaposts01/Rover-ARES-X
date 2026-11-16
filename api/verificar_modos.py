"""QA en navegador de los modos que conducen solos (ARX-11): una captura por modo y consola limpia.

Uso (desde ares_x/):  python api/verificar_modos.py
Levanta uvicorn en un puerto libre, recorre rna, difuso y ag con el veto encendido y apagado, y guarda
docs/capturas/modo_<modo>_veto_<on|off>.png. Falla si hay errores de consola o de red.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURAS = os.path.join(RAIZ, "docs", "capturas")
PASOS = 12


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    puerto = puerto_libre()
    servidor = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.servidor:app", "--port", str(puerto)],
                                cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    errores = []
    try:
        url = f"http://127.0.0.1:{puerto}/estado"
        for _ in range(120):                  # espera hasta 60 s a que uvicorn responda
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        with sync_playwright() as pw:
            navegador = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"]) \
                if os.path.exists("/opt/pw-browsers/chromium") else pw.chromium.launch()
            for modo in ("rna", "difuso", "ag"):
                for veto in (True, False):
                    pagina = navegador.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
                    pagina.on("console", lambda m, _m=modo: errores.append(f"{_m}: {m.text}") if m.type == "error" else None)
                    pagina.on("requestfailed", lambda r, _m=modo: errores.append(f"{_m}: red {r.url}"))
                    pagina.goto(f"http://127.0.0.1:{puerto}/")
                    # La página crea una partida al cargar; un cambio de modo durante la carga se descarta.
                    pagina.wait_for_load_state("networkidle")
                    pagina.click("#iniciar")          # menú de inicio (ARX-14)
                    pagina.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
                    pagina.wait_for_timeout(1000)
                    pagina.select_option("#modo", modo)
                    pagina.wait_for_timeout(800)
                    if pagina.is_checked("#veto") != veto:
                        pagina.click("#veto")
                    pagina.wait_for_timeout(800)
                    # Comprobación: el servidor debe tener el modo y el veto pedidos antes de avanzar
                    with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/estado", timeout=5) as r:
                        estado = json.load(r)
                    if estado["modo"] != modo or estado["veto"] != veto:
                        errores.append(f"{modo}/veto={veto}: el servidor tiene modo={estado['modo']} veto={estado['veto']}")
                        pagina.close()
                        continue
                    for _ in range(PASOS):
                        pagina.click("#paso")
                        pagina.wait_for_timeout(250)
                    pagina.wait_for_timeout(600)
                    nombre = f"modo_{modo}_veto_{'on' if veto else 'off'}.png"
                    pagina.screenshot(path=os.path.join(CAPTURAS, nombre))
                    print("captura", nombre)
                    pagina.close()
            navegador.close()
    finally:
        servidor.terminate()
    if errores:
        print("ERRORES DE CONSOLA/RED:")
        print("\n".join(errores))
        return 1
    print("consola limpia en los 6 casos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
