"""Verificación en el navegador del menú de inicio (ARX-14) y del historial de decisiones (ARX-15).

Uso (desde ares_x/):  python api/verificar_menu.py --url http://127.0.0.1:8765/
Comprueba: el menú aparece sin crear ninguna partida; «Iniciar partida» crea la de la semilla elegida;
el historial tiene una fila por paso y se filtra por modo; el enlace de CSV responde. Consola limpia.
Guarda docs/capturas/menu.png y docs/capturas/historial.png.
"""
import argparse
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765/")
    ap.add_argument("--salida", default=os.path.join(RAIZ, "docs", "capturas"))
    args = ap.parse_args()
    base = args.url.rstrip("/")
    errores, creaciones = [], []

    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1280, "height": 800})
        pagina.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pagina.on("pageerror", lambda e: errores.append(str(e)))
        pagina.on("request", lambda r: creaciones.append(r.url) if r.method == "POST" and "/partida" in r.url else None)
        pagina.goto(args.url, wait_until="networkidle")
        pagina.wait_for_timeout(800)

        # ARX-14: el menú aparece y no se ha creado ninguna partida
        assert pagina.is_visible("#menu"), "el menú de inicio no aparece"
        assert not creaciones, f"se creó partida sin pulsar Iniciar: {creaciones}"
        with urllib.request.urlopen(f"{base}/estado", timeout=5) as r:
            sin = json.load(r)
        print("antes de iniciar, /estado:", sin)
        pagina.screenshot(path=os.path.join(args.salida, "menu.png"))

        pagina.fill("#menu-semilla", "7")
        pagina.select_option("#menu-nivel", "2")
        pagina.click("#iniciar")
        pagina.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')",
                                 timeout=60000)
        assert not pagina.is_visible("#menu"), "el menú sigue visible tras iniciar"
        with urllib.request.urlopen(f"{base}/estado", timeout=5) as r:
            estado = json.load(r)
        assert estado["semilla"] == 7 and estado["nivel"] == 2, estado
        print("tras iniciar: semilla", estado["semilla"], "nivel", estado["nivel"])

        # ARX-15: historial con una fila por paso, filtrable por modo
        pagina.click("#historial-toggle")
        pagina.select_option("#modo", "rna")          # el modo debe ser rna para que los pasos sean de la RNA
        pagina.wait_for_timeout(600)
        pagina.select_option("#hist-modo", "rna")
        pagina.click("#paso")
        pagina.wait_for_timeout(2000)                 # el refresco del historial llega tras la respuesta del paso
        pagina.click("#paso")
        pagina.wait_for_timeout(2500)
        filas = pagina.locator("#hist-cuerpo tr").count()
        tecnicas = pagina.locator("#hist-cuerpo tr td:nth-child(4)").all_inner_texts()
        assert filas >= 2 and set(tecnicas) == {"rna"}, (filas, set(tecnicas))
        print("historial filtrado por rna:", filas, "filas, técnicas", set(tecnicas))
        href = pagina.get_attribute("#hist-csv", "href")
        with urllib.request.urlopen(base + href, timeout=5) as r:
            csv_texto = r.read().decode("utf-8")
        assert csv_texto.splitlines()[0].startswith("n,modo,accion,tecnica"), csv_texto[:80]
        print("CSV:", len(csv_texto.splitlines()) - 1, "filas de datos")
        pagina.screenshot(path=os.path.join(args.salida, "historial.png"))
        navegador.close()

    if errores:
        print("ERRORES DE CONSOLA:", errores)
        return 1
    print("consola limpia; menú y historial verificados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
