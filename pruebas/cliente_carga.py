"""
Cliente de carga (RD-F19) — genera apuestas concurrentes contra uno o
varios nodos de punto de venta, para medir RD-NF01 (latencia) y
RD-NF02 (escalado horizontal).
"""
from __future__ import annotations

import argparse
import json
import random
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, ".")
from rdpv.comun.protocolo import enviar_mensaje, recibir_mensaje


def registrar_una_apuesta(host: str, puerto: int, monto: float, timeout: float = 3.0) -> tuple[bool, float]:
    inicio = time.perf_counter()
    try:
        with socket.create_connection((host, puerto), timeout=timeout) as sock:
            sock.settimeout(timeout)
            enviar_mensaje(sock, {"tipo": "APUESTA_CLIENTE", "monto": monto})
            buffer = bytearray()
            resp = recibir_mensaje(sock, buffer)
            duracion_ms = (time.perf_counter() - inicio) * 1000.0
            exito = resp is not None and resp.get("resultado") == "ACEPTADA"
            return exito, duracion_ms
    except OSError:
        return False, (time.perf_counter() - inicio) * 1000.0


def ejecutar_carga(nodos: list[tuple[str, int]], total_apuestas: int, hilos_cliente: int,
                    monto_min: float = 1000, monto_max: float = 50000) -> dict:
    latencias = []
    exitosas = 0
    fallidas = 0

    def tarea(i: int):
        host, puerto = nodos[i % len(nodos)]
        monto = random.uniform(monto_min, monto_max)
        return registrar_una_apuesta(host, puerto, monto)

    inicio_total = time.perf_counter()
    with ThreadPoolExecutor(max_workers=hilos_cliente) as pool:
        futuros = [pool.submit(tarea, i) for i in range(total_apuestas)]
        for f in as_completed(futuros):
            exito, duracion_ms = f.result()
            latencias.append(duracion_ms)
            if exito:
                exitosas += 1
            else:
                fallidas += 1
    duracion_total = time.perf_counter() - inicio_total

    latencias.sort()
    n = len(latencias)
    p95 = latencias[min(n - 1, int(round(0.95 * (n - 1))))] if n else 0.0

    return {
        "total_apuestas": total_apuestas,
        "nodos": len(nodos),
        "hilos_cliente": hilos_cliente,
        "exitosas": exitosas,
        "fallidas": fallidas,
        "duracion_total_s": duracion_total,
        "throughput_por_s": total_apuestas / duracion_total if duracion_total > 0 else 0,
        "latencia_promedio_ms": sum(latencias) / n if n else 0,
        "latencia_p95_ms": p95,
        "latencia_max_ms": latencias[-1] if latencias else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodos", nargs="+", required=True,
                         help="Lista de nodos host:puerto, p.ej. 127.0.0.1:9101 127.0.0.1:9102")
    parser.add_argument("--total", type=int, default=1000)
    parser.add_argument("--hilos-cliente", type=int, default=50)
    parser.add_argument("--salida", default=None)
    args = parser.parse_args()

    nodos = []
    for n in args.nodos:
        host, puerto = n.split(":")
        nodos.append((host, int(puerto)))

    resultado = ejecutar_carga(nodos, args.total, args.hilos_cliente)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
