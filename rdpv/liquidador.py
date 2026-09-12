"""
Liquidador (RD-F12, RD-F13, RD-F14) — consumidor concurrente del bus,
con emisión de compensación (patrón Saga) cuando la acreditación falla.
"""
from __future__ import annotations

import argparse
import random
import sys
import threading
import time

sys.path.insert(0, ".")
from rdpv.comun.protocolo import enviar_y_recibir


class Liquidador:
    def __init__(self, liquidador_id: str, host_bus: str, puerto_bus: int,
                 host_coordinador: str, puerto_coordinador: int,
                 probabilidad_fallo: float = 0.0):
        self.liquidador_id = liquidador_id
        self._host_bus = host_bus
        self._puerto_bus = puerto_bus
        self._host_coord = host_coordinador
        self._puerto_coord = puerto_coordinador
        self._probabilidad_fallo = probabilidad_fallo
        self._detener = threading.Event()
        self.procesados = 0
        self.compensados = 0

    def iniciar(self) -> None:
        print(f"[{self.liquidador_id}] iniciado, consumiendo del bus")
        while not self._detener.is_set():
            try:
                resp = enviar_y_recibir(self._host_bus, self._puerto_bus,
                                         {"tipo": "CONSUMIR", "consumidor_id": self.liquidador_id},
                                         timeout=2.0)
            except OSError:
                time.sleep(0.5)
                continue

            if resp.get("resultado") == "VACIO":
                time.sleep(0.1)
                continue

            evento = resp["evento"]
            self._procesar(evento)

    def detener(self) -> None:
        self._detener.set()

    def _procesar(self, evento: dict) -> None:
        # Simulación deliberada de fallo de liquidación para demostrar la Saga (RD-F19).
        if random.random() < self._probabilidad_fallo:
            try:
                enviar_y_recibir(self._host_coord, self._puerto_coord, {
                    "tipo": "COMPENSAR", "clave_idem": evento["clave_idem"], "motivo": "fallo_liquidacion",
                }, timeout=1.0)
                self.compensados += 1
            except OSError:
                pass
        else:
            self.procesados += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--host-bus", default="127.0.0.1")
    parser.add_argument("--puerto-bus", type=int, default=9200)
    parser.add_argument("--host-coordinador", default="127.0.0.1")
    parser.add_argument("--puerto-coordinador", type=int, default=9000)
    parser.add_argument("--prob-fallo", type=float, default=0.0)
    args = parser.parse_args()

    Liquidador(args.id, args.host_bus, args.puerto_bus,
               args.host_coordinador, args.puerto_coordinador, args.prob_fallo).iniciar()


if __name__ == "__main__":
    main()
