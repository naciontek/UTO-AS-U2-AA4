"""
Bus de eventos (RD-F12, RD-F13) — patrón Producer-Consumer.

Cola persistente en memoria + respaldo en archivo, para que el registro
de apuestas (productor) nunca espere a la liquidación (consumidor). Los
liquidadores concurrentes consumen con `CONSUMIR`; cada evento se
entrega a un único consumidor (sin duplicar el procesamiento, RD-F13).
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
from collections import deque

from rdpv.comun.protocolo import enviar_mensaje, recibir_mensaje


class BusEventos:
    def __init__(self, host: str = "127.0.0.1", puerto: int = 9200,
                 ruta_respaldo: str = "resultados/bus_eventos.jsonl"):
        self.host = host
        self.puerto = puerto
        self._cola: deque[dict] = deque()
        self._lock = threading.Condition()
        self._ruta_respaldo = ruta_respaldo
        os.makedirs(os.path.dirname(ruta_respaldo) or ".", exist_ok=True)
        self._detener = threading.Event()
        self.total_publicados = 0
        self.total_consumidos = 0

    def iniciar(self) -> None:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((self.host, self.puerto))
        servidor.listen(256)
        print(f"[bus] escuchando en {self.host}:{self.puerto}")
        while not self._detener.is_set():
            try:
                servidor.settimeout(1.0)
                cliente, _ = servidor.accept()
            except socket.timeout:
                continue
            threading.Thread(target=self._atender, args=(cliente,), daemon=True).start()

    def detener(self) -> None:
        self._detener.set()

    def _atender(self, cliente: socket.socket) -> None:
        buffer = bytearray()
        try:
            cliente.settimeout(5.0)
            mensaje = recibir_mensaje(cliente, buffer)
            if mensaje is None:
                return
            if mensaje.get("tipo") == "PUBLICAR":
                self._publicar(mensaje["evento"])
                enviar_mensaje(cliente, {"resultado": "ENCOLADO"})
            elif mensaje.get("tipo") == "CONSUMIR":
                evento = self._consumir()
                if evento is None:
                    enviar_mensaje(cliente, {"resultado": "VACIO"})
                else:
                    enviar_mensaje(cliente, {"resultado": "OK", "evento": evento})
            else:
                enviar_mensaje(cliente, {"resultado": "ERROR"})
        except (ConnectionError, OSError):
            pass
        finally:
            cliente.close()

    def _publicar(self, evento: dict) -> None:
        with self._lock:
            self._cola.append(evento)
            self.total_publicados += 1
            self._lock.notify()
        with open(self._ruta_respaldo, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def _consumir(self) -> dict | None:
        with self._lock:
            if not self._cola:
                return None
            self.total_consumidos += 1
            return self._cola.popleft()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=9200)
    args = parser.parse_args()
    BusEventos(args.host, args.puerto).iniciar()


if __name__ == "__main__":
    main()
