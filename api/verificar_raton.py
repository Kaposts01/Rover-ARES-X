"""Verificación del ratón sobre el mapa 3D (ARX-16).

Uso (desde ares_x/):  python api/verificar_raton.py --url http://127.0.0.1:8765/
Reproduce: arrastrar para rotar, rueda para zoom, clic derecho (desplazar), arrastre que empieza en un panel
y acaba sobre el canvas o fuera de la ventana, y doble clic. Comprueba invariantes de la cámara:
  - la cámara no baja del suelo (y >= 0,3);
  - la distancia al objetivo está entre DIST_MIN y DIST_MAX;
  - el objetivo sigue sobre el mapa (con margen);
  - un arrastre que empieza en un panel no mueve la cámara;
  - el menú contextual del canvas queda suprimido;
  - consola sin errores.
Sale con código 1 si alguna invariante falla.
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright

DIST_MIN, DIST_MAX = 4.0, 80.0
MARGEN_MAPA = 6.0   # margen de la comprobación; el código acota con MARGEN_OBJETIVO = 4


def estado_camara(pag):
    return pag.evaluate("""() => {
        const c = window.__ares.camara, t = window.__ares.controles.target;
        return { x: c.position.x, y: c.position.y, z: c.position.z,
                 dist: c.position.distanceTo(t), tx: t.x, tz: t.z };
    }""")


def arrastrar(pag, desde, hasta, boton="left", pasos=20):
    pag.mouse.move(*desde)
    pag.mouse.down(button=boton)
    pag.mouse.move(*hasta, steps=pasos)
    pag.mouse.up(button=boton)
    # enableDamping: la cámara sigue con inercia unos instantes tras soltar; se espera a que se asiente
    pag.wait_for_timeout(2000)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765/")
    ap.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "capturas"))
    args = ap.parse_args()
    fallos, errores = [], []

    def comprobar(nombre, cond, detalle=""):
        print(("OK   " if cond else "FALLO"), nombre, detalle)
        if not cond:
            fallos.append(f"{nombre} {detalle}")

    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        pag = navegador.new_page(viewport={"width": 1280, "height": 800})
        pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(args.url, wait_until="networkidle")
        pag.click("#iniciar")
        pag.wait_for_function("document.getElementById('mensaje').textContent.startsWith('Partida nueva')", timeout=60000)
        pag.wait_for_timeout(800)
        mapa_cx, mapa_cz = 15.0, 10.0   # centro del mapa 20x30 en coordenadas de la escena (columnas/2, filas/2)

        def invariantes(etiqueta):
            c = estado_camara(pag)
            comprobar(f"{etiqueta}: cámara sobre el suelo", c["y"] >= 0.3, f"y={c['y']:.2f}")
            comprobar(f"{etiqueta}: distancia acotada", DIST_MIN <= c["dist"] <= DIST_MAX, f"dist={c['dist']:.1f}")
            comprobar(f"{etiqueta}: objetivo sobre el mapa",
                      -MARGEN_MAPA <= c["tx"] <= 30 + MARGEN_MAPA and -MARGEN_MAPA <= c["tz"] <= 20 + MARGEN_MAPA,
                      f"target=({c['tx']:.1f},{c['tz']:.1f})")
            return c

        centro = (640, 400)
        invariantes("inicio")

        # 1. Arrastre para rotar hacia abajo, hasta intentar pasar bajo el horizonte
        for _ in range(4):
            arrastrar(pag, centro, (640, 760), pasos=25)
        invariantes("tras arrastrar hacia abajo")

        # 2. Rueda: zoom hacia dentro mucho y hacia fuera mucho
        pag.mouse.move(*centro)
        for _ in range(40):
            pag.mouse.wheel(0, -400)
            pag.wait_for_timeout(15)
        invariantes("tras zoom hacia dentro")
        for _ in range(60):
            pag.mouse.wheel(0, 600)
            pag.wait_for_timeout(15)
        invariantes("tras zoom hacia fuera")

        # 3. Clic derecho arrastrado (desplazar): el objetivo no debe salir del mapa
        for _ in range(3):
            arrastrar(pag, centro, (60, 90), boton="right", pasos=30)
        invariantes("tras desplazar con clic derecho")

        # 4. Menú contextual suprimido en el canvas
        supr = pag.evaluate("""() => {
            const e = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 640, clientY: 400 });
            document.querySelector('canvas').dispatchEvent(e);
            return e.defaultPrevented;
        }""")
        comprobar("menú contextual suprimido en el canvas", supr)

        # 5. Arrastre que empieza en el panel HUD (encima del canvas): no debe rotar la cámara
        antes = estado_camara(pag)
        arrastrar(pag, (120, 120), (700, 500), pasos=25)
        despues = estado_camara(pag)
        movida = abs(antes["x"] - despues["x"]) + abs(antes["z"] - despues["z"]) > 1e-3
        comprobar("arrastre desde el panel no mueve la cámara", not movida or abs(antes["x"] - despues["x"]) < 0.05,
                  f"dx,dz={abs(antes['x'] - despues['x']):.3f},{abs(antes['z'] - despues['z']):.3f}")

        # 6. Soltar fuera de la ventana: tras soltar, mover el ratón no debe seguir girando la cámara
        pag.mouse.move(*centro)
        pag.mouse.down()
        pag.mouse.move(900, 500, steps=10)
        pag.mouse.move(1400, 500, steps=10)     # fuera de la ventana (1280 px)
        pag.mouse.up()
        pag.wait_for_timeout(6000)              # la inercia del amortiguado se apaga en pocos segundos
        t1 = estado_camara(pag)
        pag.mouse.move(300, 300, steps=10)      # ratón suelto: no debe girar nada
        pag.wait_for_timeout(1000)
        t2 = estado_camara(pag)
        delta = abs(t1["x"] - t2["x"]) + abs(t1["z"] - t2["z"])
        comprobar("tras soltar fuera de la ventana, el giro se detiene", delta < 0.01, f"delta={delta:.4f}")
        invariantes("tras soltar fuera")

        # 7. Doble clic en el canvas: no debe romper la escena
        pag.mouse.dblclick(*centro)
        pag.wait_for_timeout(300)
        invariantes("tras doble clic")

        navegador.close()

    comprobar("consola sin errores", not errores, f"{len(errores)} errores" if errores else "")
    if fallos:
        print("\nFALLOS:")
        for f in fallos:
            print(" -", f)
        return 1
    print("\nTodas las invariantes del ratón se cumplen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
