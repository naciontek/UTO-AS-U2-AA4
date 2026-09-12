"""
Monitor (RD-F16, RD-F17, RD-NF12) — recolector de métricas por UDP.

Agrega las métricas emitidas por todos los nodos y las escribe a un
archivo JSON al finalizar, para que las pruebas de carga puedan leerlas
y generar las gráficas de la fase de evaluación.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from collections import defaultdict


class Monitor:
    def __init__(self, host: str = "127.0.0.1", puerto: int = 9300,
                 ruta_salida: str = "resultados/metricas_monitor.json"):
        self.host = host
        self.puerto = puerto
        self._ruta_salida = ruta_salida
        self._lock = threading.Lock()
        self._muestras: dict[str, list[float]] = defaultdict(list)
        self._muestras_por_nodo: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        self._detener = threading.Event()

    def iniciar(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.puerto))
        sock.settimeout(1.0)
        print(f"[monitor] escuchando UDP en {self.host}:{self.puerto}")
        while not self._detener.is_set():
            try:
                datos, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                mensaje = json.loads(datos.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            with self._lock:
                self._muestras[mensaje["tipo"]].append(mensaje["valor"])
                self._muestras_por_nodo[mensaje["nodo_id"]][mensaje["tipo"]].append(mensaje["valor"])

    def detener_y_guardar(self) -> dict:
        self._detener.set()
        os.makedirs(os.path.dirname(self._ruta_salida) or ".", exist_ok=True)
        with self._lock:
            resultado = {
                "global": {k: self._resumen(v) for k, v in self._muestras.items()},
                "por_nodo": {
                    nodo: {tipo: self._resumen(v) for tipo, v in tipos.items()}
                    for nodo, tipos in self._muestras_por_nodo.items()
                },
            }
        with open(self._ruta_salida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        return resultado

    @staticmethod
    def _resumen(valores: list[float]) -> dict:
        if not valores:
            return {"n": 0}
        ordenados = sorted(valores)
        n = len(ordenados)
        p95_idx = min(n - 1, int(round(0.95 * (n - 1))))
        return {
            "n": n,
            "promedio": sum(ordenados) / n,
            "min": ordenados[0],
            "max": ordenados[-1],
            "p95": ordenados[p95_idx],
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=9300)
    parser.add_argument("--duracion", type=float, default=0.0,
                         help="Si es > 0, el monitor se detiene solo tras N segundos.")
    args = parser.parse_args()

    monitor = Monitor(args.host, args.puerto)
    if args.duracion > 0:
        threading.Timer(args.duracion, monitor.detener_y_guardar).start()
    monitor.iniciar()


if __name__ == "__main__":
    main()
