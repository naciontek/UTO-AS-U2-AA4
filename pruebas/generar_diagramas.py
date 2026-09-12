"""
Genera los tres diagramas UML del informe a partir de la implementación real.
Estilo visual coherente con las figuras de la Unidad 1 (cajas pastel, bordes finos).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

AZUL = "#dae8fc"; AZUL_B = "#6c8ebf"
MORADO = "#e1d5e7"; MORADO_B = "#9673a6"
VERDE = "#d5e8d4"; VERDE_B = "#82b366"
NARANJA = "#ffe6cc"; NARANJA_B = "#d79b00"
GRIS = "#f5f5f5"; GRIS_B = "#999999"
TXT = "#1a1a1a"

plt.rcParams.update({"font.family": "DejaVu Serif"})


def caja(ax, x, y, w, h, texto, fc, ec, fs=8, peso="normal", radio=0.02):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={radio}",
                       facecolor=fc, edgecolor=ec, linewidth=1.1)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center",
            fontsize=fs, color=TXT, fontweight=peso, linespacing=1.4)


def flecha(ax, p1, p2, texto="", estilo="-|>", offset=0.0, fs=6.6, rad=0.0, color="#444444"):
    # El estilo "-->" se usa en este script como marca de mensaje asíncrono o
    # de retorno; matplotlib no lo conoce, así que se traduce a línea punteada.
    punteada = (estilo == "-->")
    estilo_real = "-|>" if punteada else estilo
    a = FancyArrowPatch(p1, p2, arrowstyle=estilo_real, mutation_scale=9,
                        color=color, linewidth=1.0,
                        connectionstyle=f"arc3,rad={rad}",
                        linestyle="--" if punteada else "-")
    ax.add_patch(a)
    if texto:
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2 + offset
        ax.text(mx, my, texto, ha="center", va="center", fontsize=fs, color="#333333",
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.92))


# ===================================================================== #
# FIGURA 1 — DIAGRAMA DE COMPONENTES
# ===================================================================== #
fig, ax = plt.subplots(figsize=(11, 6.5))
ax.set_xlim(0, 11); ax.set_ylim(0.85, 7.05); ax.axis("off")

# --- Nodo de punto de venta (contenedor) ---
ax.add_patch(Rectangle((0.25, 2.5), 3.5, 4.35, facecolor="white",
                       edgecolor=AZUL_B, linewidth=1.3, linestyle="--"))
ax.text(2.0, 6.62, "«nodo» Punto de Venta  (x N)", ha="center", va="center",
        fontsize=9, fontweight="bold", color=AZUL_B)

caja(ax, 0.45, 5.75, 3.1, 0.62, "Servidor de solicitudes\n(acepta conexiones)", AZUL, AZUL_B)
caja(ax, 0.45, 4.95, 3.1, 0.62, "«Thread Pool»\nHilos trabajadores", MORADO, MORADO_B)
caja(ax, 0.45, 4.15, 1.45, 0.62, "«Monitor»\nCupo + candado", VERDE, VERDE_B, fs=7.4)
caja(ax, 2.10, 4.15, 1.45, 0.62, "«Circuit\nBreaker»", NARANJA, NARANJA_B, fs=7.4)
caja(ax, 0.45, 3.35, 1.45, 0.62, "«Outbox»\nBitácora local", VERDE, VERDE_B, fs=7.4)
caja(ax, 2.10, 3.35, 1.45, 0.62, "Hilo de latido\ny reintento", MORADO, MORADO_B, fs=7.4)
caja(ax, 0.45, 2.65, 3.1, 0.52, "Fondo de conexiones persistentes", GRIS, GRIS_B, fs=7.4)

# --- Coordinador ---
ax.add_patch(Rectangle((4.55, 3.15), 3.0, 3.7, facecolor="white",
                       edgecolor=MORADO_B, linewidth=1.3, linestyle="--"))
ax.text(6.05, 6.62, "«nodo» Coordinador", ha="center", va="center",
        fontsize=9, fontweight="bold", color=MORADO_B)

caja(ax, 4.72, 5.85, 2.66, 0.55, "Registro de nodos\ny vigilancia de latidos", MORADO, MORADO_B, fs=7.4)
caja(ax, 4.72, 5.15, 2.66, 0.55, "Validador de\nidempotencia", MORADO, MORADO_B, fs=7.4)
caja(ax, 4.72, 4.45, 2.66, 0.55, "«Observer»\nDifusor de cierre", NARANJA, NARANJA_B, fs=7.4)
caja(ax, 4.72, 3.75, 2.66, 0.55, "Compensador\n(paso de la Saga)", VERDE, VERDE_B, fs=7.4)
caja(ax, 4.72, 3.25, 2.66, 0.42, "Estado global consolidado", GRIS, GRIS_B, fs=7.2)

# --- Bus, liquidadores, monitor ---
caja(ax, 8.25, 5.35, 2.45, 0.9, "«nodo» Bus de eventos\nCola persistente\n(Producer–Consumer)",
     NARANJA, NARANJA_B, fs=7.6)
caja(ax, 8.25, 3.95, 2.45, 0.9, "«nodo» Liquidador  (x M)\nConsumo concurrente\ny compensación", VERDE, VERDE_B, fs=7.6)
caja(ax, 8.25, 2.75, 2.45, 0.8, "«nodo» Monitor\nMétricas por UDP", GRIS, GRIS_B, fs=7.6)

# --- Cliente ---
caja(ax, 0.65, 1.35, 2.7, 0.62, "Terminal del vendedor\n(cliente de carga)", GRIS, GRIS_B, fs=7.8)

# --- Conexiones ---
flecha(ax, (2.0, 1.97), (2.0, 2.63), "APUESTA_CLIENTE", offset=0.0, fs=6.4)
flecha(ax, (3.78, 5.25), (4.70, 5.42), "APUESTA / SINCRONIZAR", offset=0.16, fs=6.4)
flecha(ax, (3.78, 3.60), (4.70, 6.05), "LATIDO", offset=0.0, fs=6.4, rad=-0.22)
flecha(ax, (4.70, 4.60), (3.78, 4.42), "CIERRE (difusión)", offset=-0.17, fs=6.4)
flecha(ax, (7.42, 5.55), (8.22, 5.75), "PUBLICAR", offset=0.14, fs=6.4)
flecha(ax, (8.60, 5.32), (8.60, 4.88), "CONSUMIR", offset=0.0, fs=6.4, rad=0.0)
flecha(ax, (8.22, 4.25), (7.42, 4.02), "COMPENSAR", offset=-0.15, fs=6.4)
flecha(ax, (9.45, 3.92), (9.45, 3.58), "", fs=6.0)
# Las métricas salen de los nodos y del coordinador hacia el monitor. Se encaminan
# por debajo de ambos contenedores para no cruzar ninguna caja interna.
ax.plot([3.55, 3.55], [2.48, 1.05], linestyle="--", color="#444444", linewidth=1.0)
ax.plot([6.05, 6.05], [3.13, 1.05], linestyle="--", color="#444444", linewidth=1.0)
ax.plot([3.55, 9.45], [1.05, 1.05], linestyle="--", color="#444444", linewidth=1.0)
flecha(ax, (9.45, 1.05), (9.45, 2.72), "", fs=6.0, estilo="-->")
ax.text(6.5, 1.05, "METRICA (UDP)", ha="center", va="center", fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"))


fig.tight_layout()
fig.savefig("resultados/figura1_componentes.png", dpi=170, facecolor="white")
plt.close(fig)


# ===================================================================== #
# FIGURA 2 — DIAGRAMA DE SECUENCIA
# ===================================================================== #
fig, ax = plt.subplots(figsize=(11, 8.0))
ax.set_xlim(0, 11); ax.set_ylim(0.9, 8.3); ax.axis("off")

lineas = [
    ("Terminal\ndel vendedor", 1.0, GRIS, GRIS_B),
    ("Hilo trabajador\n(Nodo PDV)", 3.0, MORADO, MORADO_B),
    ("Candado\nde cupo", 4.9, VERDE, VERDE_B),
    ("Coordinador", 6.9, AZUL, AZUL_B),
    ("Bus de\neventos", 8.6, NARANJA, NARANJA_B),
    ("Liquidador", 10.1, VERDE, VERDE_B),
]
TOPE = 7.85
for nombre, x, fc, ec in lineas:
    caja(ax, x - 0.72, TOPE - 0.42, 1.44, 0.46, nombre, fc, ec, fs=7.4, peso="bold")
    ax.plot([x, x], [0.85, TOPE - 0.42], linestyle=(0, (4, 4)), color="#aaaaaa", linewidth=0.9)

X = {n: x for n, x, _, _ in lineas}
XT, XH, XC, XCO, XB, XL = (X["Terminal\ndel vendedor"], X["Hilo trabajador\n(Nodo PDV)"],
                            X["Candado\nde cupo"], X["Coordinador"],
                            X["Bus de\neventos"], X["Liquidador"])

pasos = [
    (7.20, XT, XH, "1. Solicita registro de apuesta", "-|>"),
    (6.85, XH, XC, "2. Adquiere el candado", "-|>"),
    (6.50, XC, XH, "3. Verifica y descuenta el cupo", "-->"),
    (6.15, XH, XCO, "4. APUESTA con clave de idempotencia", "-|>"),
]
for y, x1, x2, txt, est in pasos:
    flecha(ax, (x1, y), (x2, y), txt, estilo=est, offset=0.15, fs=6.8)

# Fragmento alt
ax.add_patch(Rectangle((2.15, 2.35), 8.5, 3.55, facecolor="none",
                       edgecolor="#8a8a8a", linewidth=1.0))
ax.add_patch(Rectangle((2.15, 5.62), 0.72, 0.28, facecolor="#ececec", edgecolor="#8a8a8a", linewidth=1.0))
ax.text(2.51, 5.76, "alt", ha="center", va="center", fontsize=7.2, fontweight="bold", color="#333333")
ax.text(3.05, 5.76, "[coordinador disponible]", ha="left", va="center", fontsize=7.0, color="#333333")

flecha(ax, (XCO, 5.35), (XH, 5.35), "5. CONFIRMADA", estilo="-->", offset=0.15, fs=6.8)
flecha(ax, (XCO, 5.00), (XB, 5.00), "6. PUBLICAR evento", estilo="-|>", offset=0.15, fs=6.8)
flecha(ax, (XH, 4.65), (XT, 4.65), "7. Entrega comprobante (vía directa)", estilo="-->", offset=0.15, fs=6.8)

ax.plot([2.15, 10.65], [4.35, 4.35], linestyle=(0, (5, 4)), color="#8a8a8a", linewidth=1.0)
ax.text(3.05, 4.18, "[coordinador inalcanzable]", ha="left", va="center", fontsize=7.0, color="#333333")

flecha(ax, (XH, 3.85), (XH + 0.95, 3.85), "", estilo="-|>", fs=6.4)
ax.plot([XH + 0.95, XH + 0.95], [3.85, 3.55], color="#444444", linewidth=1.0)
flecha(ax, (XH + 0.95, 3.55), (XH, 3.55), "", estilo="-|>", fs=6.4)
ax.text(XH + 1.08, 3.70, "8. Abre el circuito y anexa la apuesta al Outbox",
        ha="left", va="center", fontsize=6.8, color="#333333")

flecha(ax, (XH, 3.10), (XT, 3.10), "9. Entrega comprobante (aceptación provisional)", estilo="-->", offset=0.15, fs=6.8)
flecha(ax, (XH, 2.70), (XCO, 2.70), "10. SINCRONIZAR lote al restablecerse la red", estilo="-|>", offset=0.15, fs=6.8)

flecha(ax, (XB, 1.95), (XL, 1.95), "11. CONSUMIR", estilo="-->", offset=0.15, fs=6.8)
flecha(ax, (XL, 1.55), (XCO, 1.55), "12. COMPENSAR si la liquidación falla", estilo="-|>", offset=0.15, fs=6.8)


fig.tight_layout()
fig.savefig("resultados/figura2_secuencia.png", dpi=170, facecolor="white")
plt.close(fig)


# ===================================================================== #
# FIGURA 3 — DIAGRAMA DE DESPLIEGUE
# ===================================================================== #
fig, ax = plt.subplots(figsize=(11, 6.1))
ax.set_xlim(0, 11); ax.set_ylim(0.85, 6.15); ax.axis("off")

ax.add_patch(Rectangle((0.3, 0.95), 10.4, 5.1, facecolor="#fcfcfc",
                       edgecolor="#999999", linewidth=1.2, linestyle="--"))
ax.text(5.5, 5.78, "«dispositivo» Equipo anfitrión — red local 127.0.0.1",
        ha="center", va="center", fontsize=9.5, fontweight="bold", color="#444444")

caja(ax, 0.6, 3.95, 2.3, 1.45,
     "«proceso»\nnodo_pdv (x4)\n\npuertos 9101–9104\n8 hilos trabajadores",
     AZUL, AZUL_B, fs=7.6)
caja(ax, 3.35, 3.95, 2.3, 1.45,
     "«proceso»\ncoordinador\n\npuerto 9000\nun hilo por conexión",
     MORADO, MORADO_B, fs=7.6)
caja(ax, 6.10, 3.95, 2.3, 1.45,
     "«proceso»\nbus_eventos\n\npuerto 9200\ncola persistente",
     NARANJA, NARANJA_B, fs=7.6)
caja(ax, 8.85, 3.95, 1.6, 1.45,
     "«proceso»\nliquidador\n(x2)",
     VERDE, VERDE_B, fs=7.6)

caja(ax, 0.6, 2.35, 2.3, 1.05,
     "«artefacto»\noutbox_nodo-N.jsonl\nbitácora local por nodo",
     GRIS, GRIS_B, fs=7.2)
caja(ax, 3.35, 2.35, 2.3, 1.05,
     "«artefacto»\nEstado en memoria\nclaves y reservas",
     GRIS, GRIS_B, fs=7.2)
caja(ax, 6.10, 2.35, 2.3, 1.05,
     "«artefacto»\nbus_eventos.jsonl\nrespaldo de la cola",
     GRIS, GRIS_B, fs=7.2)
caja(ax, 8.85, 2.35, 1.6, 1.05,
     "«proceso»\nmonitor\npuerto UDP 9300",
     GRIS, GRIS_B, fs=7.2)

flecha(ax, (2.92, 4.68), (3.33, 4.68), "TCP", offset=0.17, fs=6.6)
flecha(ax, (5.67, 4.68), (6.08, 4.68), "TCP", offset=0.17, fs=6.6)
flecha(ax, (8.42, 4.68), (8.83, 4.68), "TCP", offset=0.17, fs=6.6)
flecha(ax, (1.75, 3.93), (1.75, 3.42), "", fs=6.0)
flecha(ax, (4.50, 3.93), (4.50, 3.42), "", fs=6.0)
flecha(ax, (7.25, 3.93), (7.25, 3.42), "", fs=6.0)
# La línea de métricas pasa por debajo de la fila de artefactos para no cruzarlos.
ax.plot([1.75, 1.75], [2.33, 2.02], linestyle="--", color="#444444", linewidth=1.0)
ax.plot([1.75, 9.65], [2.02, 2.02], linestyle="--", color="#444444", linewidth=1.0)
flecha(ax, (9.65, 2.02), (9.65, 2.33), "", fs=6.0, estilo="-->")
ax.text(5.6, 2.02, "METRICA por UDP", ha="center", va="center", fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfc", ec="none"))

caja(ax, 3.85, 1.15, 3.3, 0.62, "«artefacto» levantar.py — orquesta los procesos", GRIS, GRIS_B, fs=7.4)


fig.tight_layout()
fig.savefig("resultados/figura3_despliegue.png", dpi=170, facecolor="white")
plt.close(fig)

print("Diagramas generados en resultados/")
