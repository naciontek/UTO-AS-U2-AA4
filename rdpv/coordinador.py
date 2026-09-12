"""
Coordinador (RD-F01, RD-F02, RD-F09, RD-F10, RD-F11, RD-F16).

Punto único de coordinación (patrón Mediator, Sección 10 de la
especificación): los nodos de punto de venta nunca se hablan entre sí,
todo pasa por aquí. Responsabilidades:
  - Registrar nodos y vigilar sus latidos (Heartbeat).
  - Validar idempotencia de cada apuesta (Idempotency Key).
  - Aplicar el corte de cierre de sorteo (Observer distribuido: difunde
    el cierre a los nodos suscritos).
  - Publicar en el bus de eventos las apuestas confirmadas.
  - Revertir reservas cuando un liquidador emite una compensación (Saga).
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
from dataclasses import dataclass, field

sys.path.insert(0, ".")
from rdpv.comun.protocolo import enviar_mensaje, recibir_mensaje, enviar_y_recibir
from rdpv.comun.metricas import EmisorMetricas, Cronometro

TIMEOUT_LATIDO_SEGUNDOS = 3.0  # 3 latidos perdidos ~ RD-NF08
INTERVALO_VIGILANCIA_SEGUNDOS = 1.0


@dataclass
class EstadoNodo:
    nodo_id: str
    host: str
    puerto: int
    ultimo_latido: float
    activo: bool = True


class Coordinador:
    def __init__(self, host: str = "127.0.0.1", puerto: int = 9000,
                 host_bus: str = "127.0.0.1", puerto_bus: int = 9200,
                 host_monitor: str = "127.0.0.1", puerto_monitor: int = 9300):
        self.host = host
        self.puerto = puerto
        self._host_bus = host_bus
        self._puerto_bus = puerto_bus
        self._lock = threading.RLock()
        self._nodos: dict[str, EstadoNodo] = {}
        self._claves_procesadas: dict[str, dict] = {}  # clave_idem -> resultado
        self._sorteo_id = "SORTEO-001"
        self._sello_cierre: float | None = None
        self._reservas_activas: dict[str, str] = {}  # clave_idem -> nodo_id
        self._apuestas_confirmadas = 0
        self._apuestas_rechazadas = 0
        self._apuestas_duplicadas = 0
        self._compensaciones = 0
        self._metricas = EmisorMetricas(host_monitor, puerto_monitor, "coordinador")
        self._detener = threading.Event()

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def iniciar(self) -> None:
        hilo_vigilancia = threading.Thread(target=self._vigilar_latidos, daemon=True)
        hilo_vigilancia.start()

        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((self.host, self.puerto))
        servidor.listen(128)
        print(f"[coordinador] escuchando en {self.host}:{self.puerto}")

        while not self._detener.is_set():
            try:
                servidor.settimeout(1.0)
                cliente, _ = servidor.accept()
            except socket.timeout:
                continue
            hilo = threading.Thread(target=self._atender_conexion, args=(cliente,), daemon=True)
            hilo.start()

    def detener(self) -> None:
        self._detener.set()

    def cerrar_sorteo(self) -> None:
        with self._lock:
            self._sello_cierre = time.time()
        self._difundir_cierre()
        print(f"[coordinador] sorteo {self._sorteo_id} cerrado en t={self._sello_cierre:.3f}")

    # ------------------------------------------------------------------ #
    # Atención de mensajes
    # ------------------------------------------------------------------ #
    def _atender_conexion(self, cliente: socket.socket) -> None:
        """
        Atiende una conexión y permanece abierta leyendo mensajes en
        secuencia, porque los nodos de punto de venta la reutilizan como
        conexión persistente (ver ConexionPersistente / ajuste de la fase
        de evaluación). Termina cuando el otro extremo cierra o falla.
        """
        buffer = bytearray()
        try:
            cliente.settimeout(10.0)
            while True:
                mensaje = recibir_mensaje(cliente, buffer)
                if mensaje is None:
                    return
                respuesta = self._procesar(mensaje)
                enviar_mensaje(cliente, respuesta)
        except (ConnectionError, OSError):
            pass
        finally:
            cliente.close()

    def _procesar(self, mensaje: dict) -> dict:
        tipo = mensaje.get("tipo")
        if tipo == "REGISTRO":
            return self._on_registro(mensaje)
        if tipo == "LATIDO":
            return self._on_latido(mensaje)
        if tipo == "APUESTA":
            return self._on_apuesta(mensaje)
        if tipo == "SINCRONIZAR":
            return self._on_sincronizar(mensaje)
        if tipo == "COMPENSAR":
            return self._on_compensar(mensaje)
        if tipo == "ESTADO":
            return self._on_estado()
        return {"resultado": "ERROR", "detalle": f"tipo de mensaje desconocido: {tipo}"}

    def _on_registro(self, mensaje: dict) -> dict:
        with self._lock:
            self._nodos[mensaje["nodo_id"]] = EstadoNodo(
                nodo_id=mensaje["nodo_id"], host=mensaje.get("host", "127.0.0.1"),
                puerto=mensaje["puerto"], ultimo_latido=time.time(),
            )
        print(f"[coordinador] nodo registrado: {mensaje['nodo_id']}")
        return {"resultado": "OK", "sorteo_id": self._sorteo_id, "cerrado": self._sello_cierre is not None}

    def _on_latido(self, mensaje: dict) -> dict:
        nodo_id = mensaje["nodo_id"]
        with self._lock:
            if nodo_id in self._nodos:
                self._nodos[nodo_id].ultimo_latido = time.time()
                self._nodos[nodo_id].activo = True
            else:
                # El latido de un nodo desconocido se trata como re-registro
                # implícito: cubre el caso de que el propio coordinador se
                # haya reiniciado y perdido su estado en memoria (RD-F01).
                self._nodos[nodo_id] = EstadoNodo(
                    nodo_id=nodo_id, host="127.0.0.1", puerto=mensaje.get("puerto_nodo", 0),
                    ultimo_latido=time.time(),
                )
        if self._sello_cierre is not None:
            return {"resultado": "CIERRE", "sello_cierre": self._sello_cierre}
        return {"resultado": "OK"}

    def _on_apuesta(self, mensaje: dict) -> dict:
        clave = mensaje["clave_idem"]
        with self._lock:
            if clave in self._claves_procesadas:
                self._apuestas_duplicadas += 1
                return self._claves_procesadas[clave]

            if self._sello_cierre is not None and mensaje["sello_tiempo"] > self._sello_cierre:
                resultado = {"resultado": "RECHAZADA", "motivo": "sorteo_cerrado"}
                self._claves_procesadas[clave] = resultado
                self._apuestas_rechazadas += 1
                return resultado

            resultado = {"resultado": "CONFIRMADA", "clave_idem": clave}
            self._claves_procesadas[clave] = resultado
            self._reservas_activas[clave] = mensaje["nodo_id"]
            self._apuestas_confirmadas += 1

        self._publicar_en_bus({
            "evento": "APUESTA_CONFIRMADA",
            "clave_idem": clave,
            "nodo_id": mensaje["nodo_id"],
            "monto": mensaje["monto"],
        })
        self._metricas.emitir("apuestas_confirmadas", 1)
        return resultado

    def _on_sincronizar(self, mensaje: dict) -> dict:
        resultados = {}
        for apuesta in mensaje["lote"]:
            r = self._on_apuesta(apuesta)
            resultados[apuesta["clave_idem"]] = r["resultado"]
        return {"resultado": "OK", "detalle": resultados}

    def _on_compensar(self, mensaje: dict) -> dict:
        clave = mensaje["clave_idem"]
        with self._lock:
            self._reservas_activas.pop(clave, None)
            self._compensaciones += 1
        return {"resultado": "REVERTIDA", "clave_idem": clave}

    def _on_estado(self) -> dict:
        with self._lock:
            return {
                "resultado": "OK",
                "nodos": {nid: n.activo for nid, n in self._nodos.items()},
                "confirmadas": self._apuestas_confirmadas,
                "rechazadas": self._apuestas_rechazadas,
                "duplicadas": self._apuestas_duplicadas,
                "compensaciones": self._compensaciones,
                "sorteo_cerrado": self._sello_cierre is not None,
            }

    # ------------------------------------------------------------------ #
    # Difusión y vigilancia
    # ------------------------------------------------------------------ #
    def _difundir_cierre(self) -> None:
        with self._lock:
            nodos = list(self._nodos.values())
        for nodo in nodos:
            try:
                enviar_y_recibir(nodo.host, nodo.puerto,
                                  {"tipo": "CIERRE", "sorteo_id": self._sorteo_id,
                                   "sello_cierre": self._sello_cierre}, timeout=1.0)
            except OSError:
                pass  # El nodo lo sabrá por su propio latido; no es una falla crítica aquí.

    def _publicar_en_bus(self, evento: dict) -> None:
        try:
            enviar_y_recibir(self._host_bus, self._puerto_bus,
                              {"tipo": "PUBLICAR", "evento": evento}, timeout=1.0)
        except OSError as e:
            print(f"[coordinador] no se pudo publicar en el bus: {e}")

    def _vigilar_latidos(self) -> None:
        while not self._detener.is_set():
            time.sleep(INTERVALO_VIGILANCIA_SEGUNDOS)
            ahora = time.time()
            with self._lock:
                for nodo in self._nodos.values():
                    activo_antes = nodo.activo
                    nodo.activo = (ahora - nodo.ultimo_latido) <= TIMEOUT_LATIDO_SEGUNDOS
                    if activo_antes and not nodo.activo:
                        print(f"[coordinador] nodo caído detectado: {nodo.nodo_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=9000)
    parser.add_argument("--host-bus", default="127.0.0.1")
    parser.add_argument("--puerto-bus", type=int, default=9200)
    parser.add_argument("--host-monitor", default="127.0.0.1")
    parser.add_argument("--puerto-monitor", type=int, default=9300)
    args = parser.parse_args()

    coordinador = Coordinador(args.host, args.puerto, args.host_bus, args.puerto_bus,
                               args.host_monitor, args.puerto_monitor)
    coordinador.iniciar()


if __name__ == "__main__":
    main()
