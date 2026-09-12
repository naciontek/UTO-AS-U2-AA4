"""Genera las gráficas de la fase de evaluación a partir de los JSON en resultados/."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

NAVY = "#1a2b4c"
GOLD = "#c9a227"
ICE = "#e8edf3"
GRAY = "#5a6472"

plt.rcParams.update({
    "font.family": "DejaVu Serif", "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": GRAY, "axes.labelcolor": NAVY, "text.color": NAVY,
    "xtick.color": GRAY, "ytick.color": GRAY, "axes.grid": True,
    "grid.color": ICE, "grid.linewidth": 1.2,
})

# --- Escalado horizontal: antes y después del ajuste ---
# Valores "antes" tomados de la corrida inicial (conexión nueva por apuesta),
# con el mismo cupo y carga que la corrida "después" (5000 apuestas, 100 hilos cliente).
despues_n = [1, 2, 3, 4]
despues_v1 = [1080.5, 1079.7, 1019.9, 1027.8]
despues_v2 = []
for n in despues_n:
    with open(f"resultados/escalado_{n}nodos_v2.json") as f:
        despues_v2.append(json.load(f)["throughput_por_s"])

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(despues_n, despues_v1, marker="o", color=GRAY, label="Antes del ajuste (conexión por apuesta)", linewidth=2)
ax.plot(despues_n, despues_v2, marker="o", color=GOLD, label="Después del ajuste (conexión persistente)", linewidth=2)
ideal = [despues_v2[0] * n for n in despues_n]
ax.plot(despues_n, ideal, linestyle="--", color=NAVY, alpha=0.5, label="Escalado lineal ideal (referencia)")
ax.set_xlabel("Número de nodos de punto de venta")
ax.set_ylabel("Throughput (apuestas/segundo)")
ax.set_title("Escalado horizontal antes y después del ajuste", color=NAVY, fontsize=13, fontweight="bold")
ax.legend(fontsize=9)
ax.set_xticks(despues_n)
fig.tight_layout()
fig.savefig("resultados/grafica_escalado_horizontal.png", dpi=150)
plt.close(fig)

# --- Saturación de hilos ---
with open("resultados/saturacion_hilos.json") as f:
    sat = json.load(f)
hilos = [s["hilos_nodo"] for s in sat]
throughput = [s["throughput_por_s"] for s in sat]
p95 = [s["latencia_p95_ms"] for s in sat]

fig, ax1 = plt.subplots(figsize=(7, 4.5))
ax1.plot(hilos, throughput, marker="o", color=NAVY, linewidth=2, label="Throughput")
ax1.set_xlabel("Hilos trabajadores del nodo")
ax1.set_ylabel("Throughput (apuestas/segundo)", color=NAVY)
ax1.set_xscale("log", base=2)
ax1.set_xticks(hilos)
ax1.set_xticklabels(hilos)

ax2 = ax1.twinx()
ax2.plot(hilos, p95, marker="s", color=GOLD, linewidth=2, label="Latencia p95")
ax2.set_ylabel("Latencia p95 (ms)", color=GOLD)
ax2.grid(False)

ax1.set_title("Saturación de hilos dentro de un nodo", color=NAVY, fontsize=13, fontweight="bold")
idx_pico = throughput.index(max(throughput))
ax1.annotate(f"Punto de saturación\n({hilos[idx_pico]} hilos)",
             xy=(hilos[idx_pico], throughput[idx_pico]),
             xytext=(hilos[idx_pico] * 0.6, throughput[idx_pico] * 0.75),
             arrowprops=dict(arrowstyle="->", color=GRAY), fontsize=9, color=GRAY)
fig.tight_layout()
fig.savefig("resultados/grafica_saturacion_hilos.png", dpi=150)
plt.close(fig)

print("Gráficas generadas en resultados/")
