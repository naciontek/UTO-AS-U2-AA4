"""
Outbox con sincronización diferida (RD-F06, RD-F08, RD-NF05, RD-NF06).

Cada nodo de punto de venta mantiene su propia bitácora de salida en un
archivo JSON local. Cuando el coordinador es inalcanzable, la apuesta
(ya confirmada localmente, con el cupo ya descontado) se anexa aquí.
Un hilo de reintento la reenvía en orden al restablecerse la conexión.

El orden importa: si se publicara primero en el bus y la operación local
fallara después, el sistema anunciaría algo que nunca ocurrió (lección
heredada de la Saga de la Unidad 1). Por eso la escritura en el outbox
ocurre en la misma sección donde se confirma la apuesta localmente.
"""
from __future__ import annotations

import json
import os
import threading
from typing import Iterator


class Outbox:
    def __init__(self, ruta_archivo: str):
        self._ruta = ruta_archivo
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(ruta_archivo) or ".", exist_ok=True)
        if not os.path.exists(self._ruta):
            open(self._ruta, "a", encoding="utf-8").close()

    def anexar(self, registro: dict) -> None:
        with self._lock:
            with open(self._ruta, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    def pendientes(self) -> list[dict]:
        with self._lock:
            if not os.path.exists(self._ruta):
                return []
            with open(self._ruta, "r", encoding="utf-8") as f:
                lineas = [l for l in f.read().splitlines() if l.strip()]
            return [json.loads(l) for l in lineas]

    def limpiar_confirmados(self, claves_confirmadas: set[str]) -> None:
        """Reescribe el archivo dejando solo lo que aún no se sincronizó."""
        with self._lock:
            restantes = []
            if os.path.exists(self._ruta):
                with open(self._ruta, "r", encoding="utf-8") as f:
                    for linea in f.read().splitlines():
                        if not linea.strip():
                            continue
                        registro = json.loads(linea)
                        if registro["clave_idem"] not in claves_confirmadas:
                            restantes.append(linea)
            with open(self._ruta, "w", encoding="utf-8") as f:
                for linea in restantes:
                    f.write(linea + "\n")

    def cantidad_pendiente(self) -> int:
        return len(self.pendientes())
