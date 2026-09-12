"""
Levanta la red distribuida completa con un solo comando (RD-NF13):
1 coordinador, 1 bus de eventos, 1 monitor, N nodos de punto de venta
y M liquidadores, todos como procesos independientes.

Uso:
    python levantar.py --nodos 4 --liquidadores 2 --hilos-por-nodo 8

Ctrl+C detiene todos los procesos hijos de forma ordenada.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

PROCESOS: list[subprocess.Popen] = []


def lanzar(comando: list[str]) -> subprocess.Popen:
    p = subprocess.Popen(comando, cwd=os.path.dirname(os.path.abspath(__file__)))
    PROCESOS.append(p)
    return p


def detener_todo(*_args):
    print("\n[levantar] deteniendo la red...")
    for p in PROCESOS:
        try:
            p.terminate()
        except ProcessLookupError:
            pass
    time.sleep(1.0)
    for p in PROCESOS:
        if p.poll() is None:
            p.kill()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodos", type=int, default=4)
    parser.add_argument("--liquidadores", type=int, default=2)
    parser.add_argument("--hilos-por-nodo", type=int, default=8)
    parser.add_argument("--cupo-por-nodo", type=float, default=50_000_000.0)
    parser.add_argument("--prob-fallo-liquidacion", type=float, default=0.0)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, detener_todo)
    signal.signal(signal.SIGTERM, detener_todo)

    py = sys.executable
    os.makedirs("resultados", exist_ok=True)

    print("[levantar] iniciando monitor...")
    lanzar([py, "-m", "rdpv.monitor"])
    time.sleep(0.3)

    print("[levantar] iniciando bus de eventos...")
    lanzar([py, "-m", "rdpv.bus_eventos"])
    time.sleep(0.3)

    print("[levantar] iniciando coordinador...")
    lanzar([py, "-m", "rdpv.coordinador"])
    time.sleep(0.5)

    for i in range(1, args.liquidadores + 1):
        print(f"[levantar] iniciando liquidador-{i}...")
        lanzar([py, "-m", "rdpv.liquidador", "--id", f"liquidador-{i}",
                "--prob-fallo", str(args.prob_fallo_liquidacion)])

    for i in range(1, args.nodos + 1):
        puerto = 9100 + i
        print(f"[levantar] iniciando nodo-{i} en puerto {puerto}...")
        lanzar([py, "-m", "rdpv.nodo_pdv", "--id", f"nodo-{i}", "--puerto", str(puerto),
                "--cupo", str(args.cupo_por_nodo), "--hilos", str(args.hilos_por_nodo)])
        time.sleep(0.2)

    print(f"\n[levantar] red activa: 1 coordinador, 1 bus, 1 monitor, "
          f"{args.nodos} nodos, {args.liquidadores} liquidadores.")
    print("[levantar] presiona Ctrl+C para detener.\n")

    while True:
        time.sleep(1.0)
        for p in PROCESOS:
            if p.poll() is not None:
                print(f"[levantar] atención: un proceso terminó de forma inesperada (pid {p.pid})")


if __name__ == "__main__":
    main()
