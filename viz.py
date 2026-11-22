"""ARES-X · figuras 2D para el notebook y el informe: matriz de confusión de la RNA y ablación de políticas.

Funciones puras: reciben datos ya calculados y devuelven la figura de matplotlib. No leen archivos ni usan el
motor, y no muestran ni cierran la figura (quien llama decide). Paleta de Okabe-Ito, segura ante daltonismo;
la información no depende solo del color (cada barra lleva su valor escrito y el híbrido lleva trama).
"""
import matplotlib

matplotlib.use("Agg", force=False)  # no interfiere si ya hay otro backend activo
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

COLOR_BASE = "#0072B2"       # azul
COLOR_HIBRIDO = "#E69F00"    # naranja
COLOR_ERROR = "#555555"      # gris para barras de desviación

ROTULOS_VARIANTES = {
    "hibrido": "Híbrido",
    "sin_rna": "Sin RNA",
    "sin_difuso": "Sin difuso",
    "sin_ag_vecino": "Sin AG (vecino más cercano)",
    "sin_ag_mas_corta": "Sin AG (ruta más corta)",
    "sin_ag_2opt": "Sin AG (vecino + 2-opt)",
    "ag_puro": "Solo AG",
    "ruta_corta": "Ruta corta voraz",
}


def plot_matriz_confusion(matriz, etiquetas, titulo="Matriz de confusión de la RNA"):
    """Matriz de confusión con conteos y porcentaje por fila (real). Filas = clase real, columnas = predicha."""
    arr = np.asarray(matriz, dtype=float)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1] or arr.shape[0] != len(etiquetas):
        raise ValueError("La matriz debe ser cuadrada y tener una etiqueta por clase.")
    n = len(etiquetas)
    totales = arr.sum(axis=1, keepdims=True)
    # Fila sin muestras: 0 % (sin dividir por cero)
    pct = np.divide(arr, totales, out=np.zeros_like(arr), where=totales > 0)
    fig, ax = plt.subplots(figsize=(6.2, 5.2), constrained_layout=True)
    im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=1)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("Fracción de la clase real")
    ax.set_xticks(range(n), list(etiquetas))
    ax.set_yticks(range(n), [f"{e}\n(n = {int(t)})" for e, t in zip(etiquetas, totales[:, 0])])
    ax.set_xlabel("Clase predicha")
    ax.set_ylabel("Clase real")
    ax.set_title(titulo)
    for i in range(n):
        for j in range(n):
            color = "white" if pct[i, j] > 0.5 else "black"
            ax.text(j, i, f"{int(arr[i, j])}\n{pct[i, j] * 100:.1f} %", ha="center", va="center",
                    color=color, fontsize=11, fontweight="bold" if i == j else "normal")
    return fig


def _rotulo(variante):
    return ROTULOS_VARIANTES.get(variante, str(variante).replace("_", " ").capitalize())


def plot_ablacion(variantes, escenario=None):
    """Compara variantes: tasa de éxito, pasos y colisiones por misión.

    `variantes` es el diccionario publicado en la comparación de políticas: nombre -> {tasa_exito, n,
    pasos: {media, desviacion}, colisiones: {media}}. El híbrido se destaca con otro color y trama.
    """
    nombres = list(variantes)
    fig, axes = plt.subplots(1, 3, figsize=(13, max(3.2, 0.55 * len(nombres) + 1.6)), sharey=True,
                             constrained_layout=True)
    if not nombres:
        for ax in axes:
            ax.set_axis_off()
        axes[0].text(0.5, 0.5, "Sin datos de ablación", ha="center", va="center", transform=axes[0].transAxes)
        return fig
    y = np.arange(len(nombres))
    colores = [COLOR_HIBRIDO if v == "hibrido" else COLOR_BASE for v in nombres]
    tramas = ["//" if v == "hibrido" else "" for v in nombres]

    def barras(ax, valores, errores, titulo, xlabel, fmt, tope=None):
        b = ax.barh(y, valores, xerr=errores, color=colores, edgecolor="black", linewidth=0.8,
                    error_kw={"ecolor": COLOR_ERROR, "capsize": 3})
        for rect, t in zip(b, tramas):
            rect.set_hatch(t)
        borde = tope if tope is not None else max(max(valores, default=0), 1e-9) * 1.35
        ax.set_xlim(0, borde)
        for yi, v in zip(y, valores):
            ax.text(v + borde * 0.02 + (0 if errores is None else errores[yi]), yi, fmt(v), va="center", fontsize=9)
        ax.set_title(titulo)
        ax.set_xlabel(xlabel)
        ax.grid(axis="x", alpha=0.3)
        ax.set_axisbelow(True)

    exito = [float(variantes[v].get("tasa_exito", 0.0)) for v in nombres]
    pasos = [float(variantes[v].get("pasos", {}).get("media", 0.0)) for v in nombres]
    desv = np.array([float(variantes[v].get("pasos", {}).get("desviacion", 0.0)) for v in nombres])
    colis = [float(variantes[v].get("colisiones", {}).get("media", 0.0)) for v in nombres]
    barras(axes[0], exito, None, "Tasa de éxito", "Misiones exitosas (%)", lambda v: f"{v:.0f} %", tope=125)
    axes[0].set_xticks(range(0, 101, 20))
    barras(axes[1], pasos, desv, "Pasos por misión", "Pasos (media ± desviación)", lambda v: f"{v:.1f}")
    barras(axes[2], colis, None, "Colisiones", "Colisiones por misión (media)", lambda v: f"{v:.2f}")
    axes[0].set_yticks(y, [_rotulo(v) for v in nombres])
    axes[0].invert_yaxis()
    ns = {int(variantes[v].get("n", 0)) for v in nombres}
    sub = f" · {escenario}" if escenario else ""
    n_txt = f" · {ns.pop()} semillas por variante" if len(ns) == 1 else ""
    fig.suptitle(f"Ablación de políticas{sub}{n_txt}")
    return fig
