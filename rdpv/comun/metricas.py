"""
Instrumentación (RD-F17, RD-NF12).

Cada nodo envía métricas al monitor mediante mensajes UDP "dispara y
olvida": la observabilidad no debe competir con el registro de apuestas
por las mismas conexiones TCP, y perder una métrica ocasional no es
crítico, mientras que perder una apuesta sí lo es. Esta asimetría es
intencional.
"""
from __future__ import annotations

import json
import socket
import time


class EmisorMetricas:
    def __init__(self, host_monitor: str, puerto_monitor: int, nodo_id: str):
        self._destino = (host_monitor, puerto_monitor)
        self._nodo_id = nodo_id
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emitir(self, tipo: str, valor: float, extra: dict | None = None) -> None:
        mensaje = {
            "nodo_id": self._nodo_id,
            "tipo": tipo,
            "valor": valor,
            "sello_tiempo": time.time(),
        }
        if extra:
            mensaje["extra"] = extra
        try:
            self._sock.sendto(json.dumps(mensaje).encode("utf-8"), self._destino)
        except OSError:
            pass  # La pérdida de una métrica no debe afectar la operación de negocio.

    def cerrar(self) -> None:
        self._sock.close()


class Cronometro:
    """Utilidad de medición de latencia con soporte de contexto (`with`)."""

    def __init__(self, emisor: EmisorMetricas | None, tipo: str):
        self._emisor = emisor
        self._tipo = tipo
        self._inicio = 0.0
        self.duracion_ms = 0.0

    def __enter__(self):
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duracion_ms = (time.perf_counter() - self._inicio) * 1000.0
        if self._emisor is not None:
            self._emisor.emitir(self._tipo, self.duracion_ms)
        return False
