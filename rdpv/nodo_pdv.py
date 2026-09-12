"""
Nodo de Punto de Venta (RD-F03, RD-F04, RD-F05, RD-F06, RD-F07, RD-F08).

Cada instancia es un proceso independiente. Internamente usa un
conjunto de hilos trabajadores (Thread Pool) para atender apuestas
concurrentes, un candado (Monitor / exclusión mutua) para proteger el
cupo compartido, un Outbox para sobrevivir a la desconexión del
coordinador, y un Circuit Breaker que evita que un coordinador lento
agote los hilos del propio nodo.
"""
from __future__ import annotations

import argparse
import queue
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")
from rdpv.comun.protocolo import (
    enviar_mensaje, recibir_mensaje, enviar_y_recibir, nueva_clave_idempotencia,
    ConexionPersistente,
)
from rdpv.comun.circuito import CircuitBreaker, CircuitoAbiertoError, RechazoDeNegocio
from rdpv.comun.outbox import Outbox
from rdpv.comun.metricas import EmisorMetricas, Cronometro

INTERVALO_LATIDO_SEGUNDOS = 1.0
INTERVALO_REINTENTO_SEGUNDOS = 1.0


class NodoPDV:
    def __init__(self, nodo_id: str, puerto: int, cupo_inicial: float,
                 num_hilos: int = 8,
                 host_coordinador: str = "127.0.0.1", puerto_coordinador: int = 9000,
                 host_monitor: str = "127.0.0.1", puerto_monitor: int = 9300,
                 dir_datos: str = "resultados"):
        self.nodo_id = nodo_id
        self.host = "127.0.0.1"
        self.puerto = puerto
        self._host_coord = host_coordinador
        self._puerto_coord = puerto_coordinador
        self._cupo = cupo_inicial
        self._cupo_lock = threading.Lock()  # Monitor: exclusión mutua sobre el cupo (RD-F04)
        self._pool = ThreadPoolExecutor(max_workers=num_hilos, thread_name_prefix=f"pdv-{nodo_id}")
        self._circuito = CircuitBreaker(umbral_fallos=3, ventana_segundos=5.0, espera_reset_segundos=2.0)

        # Ajuste de la fase de evaluación: un pequeño fondo de conexiones
        # persistentes hacia el coordinador, en lugar de abrir una conexión
        # TCP nueva por cada apuesta. El fondo tiene el mismo tamaño que el
        # conjunto de hilos del nodo, así cada hilo trabajador puede tomar
        # una conexión sin esperar a los demás.
        self._fondo_conexiones: queue.Queue[ConexionPersistente] = queue.Queue()
        for _ in range(num_hilos):
            self._fondo_conexiones.put(ConexionPersistente(host_coordinador, puerto_coordinador, timeout=1.5))
        self._outbox = Outbox(f"{dir_datos}/outbox_{nodo_id}.jsonl")
        self._metricas = EmisorMetricas(host_monitor, puerto_monitor, nodo_id)
        self._cerrado = False
        self._sello_cierre: float | None = None
        self._detener = threading.Event()
        self._num_hilos = num_hilos

        # Contadores locales (para el reporte final del nodo)
        self._contador_lock = threading.Lock()
        self._confirmadas_directas = 0
        self._enviadas_a_outbox = 0
        self._rechazadas = 0
        self._sincronizadas_ok = 0

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def iniciar(self) -> None:
        self._registrar()
        threading.Thread(target=self._emitir_latidos, daemon=True).start()
        threading.Thread(target=self._reintentar_outbox, daemon=True).start()

        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((self.host, self.puerto))
        servidor.listen(256)
        print(f"[{self.nodo_id}] escuchando en {self.host}:{self.puerto} "
              f"con {self._num_hilos} hilos, cupo inicial {self._cupo}")

        while not self._detener.is_set():
            try:
                servidor.settimeout(1.0)
                cliente, _ = servidor.accept()
            except socket.timeout:
                continue
            self._pool.submit(self._atender_conexion, cliente)

    def detener(self) -> None:
        self._detener.set()
        self._pool.shutdown(wait=False)

    # ------------------------------------------------------------------ #
    # Registro con el coordinador (RD-F01)
    # ------------------------------------------------------------------ #
    def _registrar(self) -> None:
        try:
            resp = enviar_y_recibir(self._host_coord, self._puerto_coord, {
                "tipo": "REGISTRO", "nodo_id": self.nodo_id,
                "host": self.host, "puerto": self.puerto, "cupo_inicial": self._cupo,
            })
            if resp.get("cerrado"):
                self._cerrado = True
        except OSError:
            print(f"[{self.nodo_id}] coordinador inalcanzable al registrar; reintentará vía latidos")

    def _emitir_latidos(self) -> None:
        secuencia = 0
        while not self._detener.is_set():
            time.sleep(INTERVALO_LATIDO_SEGUNDOS)
            secuencia += 1
            try:
                resp = enviar_y_recibir(self._host_coord, self._puerto_coord, {
                    "tipo": "LATIDO", "nodo_id": self.nodo_id, "secuencia": secuencia,
                    "pendientes": self._outbox.cantidad_pendiente(), "puerto_nodo": self.puerto,
                }, timeout=1.0)
                if resp.get("resultado") == "CIERRE" and not self._cerrado:
                    self._cerrado = True
                    self._sello_cierre = resp["sello_cierre"]
                    print(f"[{self.nodo_id}] cierre de sorteo recibido por latido")
            except OSError:
                pass  # El coordinador está inalcanzable; el nodo sigue operando (RD-F07).

    # ------------------------------------------------------------------ #
    # Atención de solicitudes de apuesta
    # ------------------------------------------------------------------ #
    def _atender_conexion(self, cliente: socket.socket) -> None:
        buffer = bytearray()
        try:
            cliente.settimeout(5.0)
            mensaje = recibir_mensaje(cliente, buffer)
            if mensaje is None:
                return
            if mensaje.get("tipo") == "CIERRE":
                self._cerrado = True
                self._sello_cierre = mensaje["sello_cierre"]
                enviar_mensaje(cliente, {"resultado": "OK"})
                return
            if mensaje.get("tipo") == "APUESTA_CLIENTE":
                respuesta = self._registrar_apuesta(mensaje["monto"])
                enviar_mensaje(cliente, respuesta)
                return
            enviar_mensaje(cliente, {"resultado": "ERROR", "detalle": "tipo no soportado"})
        except (ConnectionError, OSError):
            pass
        finally:
            cliente.close()

    def _registrar_apuesta(self, monto: float) -> dict:
        with Cronometro(self._metricas, "latencia_apuesta_ms") as crono:
            sello = time.time()

            if self._cerrado and self._sello_cierre is not None and sello > self._sello_cierre:
                with self._contador_lock:
                    self._rechazadas += 1
                return {"resultado": "RECHAZADA", "motivo": "sorteo_cerrado"}

            # --- Sección crítica: exclusión mutua sobre el cupo (RD-F04) ---
            with self._cupo_lock:
                if self._cupo < monto:
                    return {"resultado": "RECHAZADA", "motivo": "cupo_insuficiente"}
                self._cupo -= monto
            # --- Fin de la sección crítica ---

            clave = nueva_clave_idempotencia()
            apuesta = {"tipo": "APUESTA", "clave_idem": clave, "nodo_id": self.nodo_id,
                       "monto": monto, "sello_tiempo": sello}

            try:
                resp = self._circuito.ejecutar(self._enviar_al_coordinador, apuesta)
                if resp.get("resultado") == "RECHAZADA":
                    with self._cupo_lock:
                        self._cupo += monto  # se devuelve el cupo reservado
                    with self._contador_lock:
                        self._rechazadas += 1
                    return resp
                with self._contador_lock:
                    self._confirmadas_directas += 1
                return {"resultado": "ACEPTADA", "clave_idem": clave, "via": "directa"}

            except (OSError, CircuitoAbiertoError):
                # Camino sin conexión: se preserva localmente (Outbox, RD-F06/RD-F07)
                self._outbox.anexar(apuesta)
                with self._contador_lock:
                    self._enviadas_a_outbox += 1
                self._metricas.emitir("apuestas_a_outbox", 1)
                return {"resultado": "ACEPTADA", "clave_idem": clave, "via": "outbox"}

    def _enviar_al_coordinador(self, apuesta: dict) -> dict:
        conexion = self._fondo_conexiones.get()
        try:
            resp = conexion.enviar_y_recibir(apuesta)
        finally:
            self._fondo_conexiones.put(conexion)
        if resp.get("resultado") == "RECHAZADA":
            raise RechazoDeNegocio(resp.get("motivo", "rechazo"))
        return resp

    # ------------------------------------------------------------------ #
    # Sincronización diferida del outbox (RD-F08, RD-F09)
    # ------------------------------------------------------------------ #
    def _reintentar_outbox(self) -> None:
        while not self._detener.is_set():
            time.sleep(INTERVALO_REINTENTO_SEGUNDOS)
            pendientes = self._outbox.pendientes()
            if not pendientes:
                continue
            try:
                resp = enviar_y_recibir(self._host_coord, self._puerto_coord, {
                    "tipo": "SINCRONIZAR", "lote": pendientes,
                }, timeout=3.0)
                if resp.get("resultado") == "OK":
                    confirmadas = {
                        clave for clave, r in resp["detalle"].items()
                        if r in ("CONFIRMADA", "RECHAZADA")
                    }
                    self._outbox.limpiar_confirmados(confirmadas)
                    with self._contador_lock:
                        self._sincronizadas_ok += len(confirmadas)
                    if confirmadas:
                        print(f"[{self.nodo_id}] sincronizadas {len(confirmadas)} apuestas del outbox")
            except OSError:
                continue  # Sigue sin haber conexión; se reintenta en el próximo ciclo.

    def reporte(self) -> dict:
        with self._contador_lock:
            return {
                "nodo_id": self.nodo_id,
                "cupo_restante": self._cupo,
                "confirmadas_directas": self._confirmadas_directas,
                "enviadas_a_outbox": self._enviadas_a_outbox,
                "sincronizadas_ok": self._sincronizadas_ok,
                "rechazadas": self._rechazadas,
                "pendientes_outbox": self._outbox.cantidad_pendiente(),
                "aperturas_circuito": self._circuito.aperturas_totales,
            }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--puerto", type=int, required=True)
    parser.add_argument("--cupo", type=float, default=10_000_000.0)
    parser.add_argument("--hilos", type=int, default=8)
    parser.add_argument("--host-coordinador", default="127.0.0.1")
    parser.add_argument("--puerto-coordinador", type=int, default=9000)
    parser.add_argument("--host-monitor", default="127.0.0.1")
    parser.add_argument("--puerto-monitor", type=int, default=9300)
    args = parser.parse_args()

    nodo = NodoPDV(args.id, args.puerto, args.cupo, args.hilos,
                    args.host_coordinador, args.puerto_coordinador,
                    args.host_monitor, args.puerto_monitor)
    nodo.iniciar()


if __name__ == "__main__":
    main()
