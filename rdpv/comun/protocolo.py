"""
Protocolo de comunicación de la Red Distribuida de Puntos de Venta (RDPV).

Transporte: TCP con mensajes JSON delimitados por salto de línea ("\n").
Se eligió texto plano en lugar de un formato binario porque permite
inspeccionar el tráfico durante la sustentación, lo cual tiene valor
demostrativo (ver Sección 8 de la especificación de arquitectura).
"""
from __future__ import annotations

import json
import socket
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

TERMINADOR = b"\n"
TAMANO_BUFFER = 65536


def nueva_clave_idempotencia() -> str:
    """Genera una clave de idempotencia única en el nodo de origen (RD-F05)."""
    return uuid.uuid4().hex


def enviar_mensaje(sock: socket.socket, mensaje: dict) -> None:
    datos = (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(datos)


def recibir_mensaje(sock: socket.socket, buffer: bytearray) -> Optional[dict]:
    """
    Lee del socket hasta completar una línea JSON. `buffer` es el buffer
    de lectura persistente de la conexión (puede llegar más de un
    mensaje por lectura, o un mensaje partido en varias lecturas).
    Devuelve None si la conexión se cerró sin datos.
    """
    while TERMINADOR not in buffer:
        trozo = sock.recv(TAMANO_BUFFER)
        if not trozo:
            return None
        buffer.extend(trozo)
    linea, _, resto = buffer.partition(TERMINADOR)
    del buffer[: len(linea) + 1]
    buffer[:] = resto
    if not linea:
        return None
    return json.loads(linea.decode("utf-8"))


def enviar_y_recibir(host: str, puerto: int, mensaje: dict, timeout: float = 2.0) -> dict:
    """
    Envía un mensaje y espera una única respuesta, abriendo una conexión
    TCP nueva cada vez. Sirve para llamadas ocasionales (registro,
    sincronización de outbox, consultas de estado). Lanza OSError si el
    destino es inalcanzable o el timeout se cumple: ese error es lo que
    activa las rutas de tolerancia a fallos (Outbox, Circuit Breaker).
    """
    with socket.create_connection((host, puerto), timeout=timeout) as sock:
        sock.settimeout(timeout)
        enviar_mensaje(sock, mensaje)
        buffer = bytearray()
        respuesta = recibir_mensaje(sock, buffer)
        if respuesta is None:
            raise ConnectionError("El destino cerró la conexión sin responder")
        return respuesta


class ConexionPersistente:
    """
    Conexión TCP reutilizada hacia un mismo destino (p. ej. de un nodo
    de punto de venta hacia el coordinador). Se introdujo como ajuste de
    la fase de evaluación: abrir y cerrar una conexión por cada apuesta
    resultó ser el cuello de botella real del sistema (ver Sección de
    evaluación del informe), no la capacidad de cómputo de los nodos.

    Es segura para llamadas concurrentes de varios hilos porque serializa
    el uso del socket con un candado; el costo que evita no es la
    concurrencia sino el establecimiento repetido de la conexión TCP.
    """

    def __init__(self, host: str, puerto: int, timeout: float = 2.0):
        self._host = host
        self._puerto = puerto
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._buffer = bytearray()
        self._lock_conexion = None  # se inyecta perezosamente para evitar import circular de threading

    def _obtener_lock(self):
        if self._lock_conexion is None:
            import threading
            self._lock_conexion = threading.Lock()
        return self._lock_conexion

    def _conectar(self) -> None:
        self._sock = socket.create_connection((self._host, self._puerto), timeout=self._timeout)
        self._sock.settimeout(self._timeout)
        self._buffer = bytearray()

    def enviar_y_recibir(self, mensaje: dict) -> dict:
        with self._obtener_lock():
            if self._sock is None:
                self._conectar()
            try:
                enviar_mensaje(self._sock, mensaje)
                respuesta = recibir_mensaje(self._sock, self._buffer)
                if respuesta is None:
                    raise ConnectionError("conexión cerrada por el destino")
                return respuesta
            except (OSError, ConnectionError):
                # La conexión se perdió: se descarta y se reintenta una vez
                # con una conexión nueva antes de propagar el error.
                try:
                    if self._sock is not None:
                        self._sock.close()
                finally:
                    self._sock = None
                self._conectar()
                enviar_mensaje(self._sock, mensaje)
                respuesta = recibir_mensaje(self._sock, self._buffer)
                if respuesta is None:
                    raise ConnectionError("conexión cerrada por el destino tras reintento")
                return respuesta

    def cerrar(self) -> None:
        with self._obtener_lock():
            if self._sock is not None:
                try:
                    self._sock.close()
                finally:
                    self._sock = None


@dataclass
class Apuesta:
    clave_idem: str
    nodo_id: str
    monto: float
    sello_tiempo: float
    canal: str = "fisico"

    def a_dict(self) -> dict:
        return {
            "clave_idem": self.clave_idem,
            "nodo_id": self.nodo_id,
            "monto": self.monto,
            "sello_tiempo": self.sello_tiempo,
            "canal": self.canal,
        }

    @staticmethod
    def desde_dict(d: dict) -> "Apuesta":
        return Apuesta(
            clave_idem=d["clave_idem"],
            nodo_id=d["nodo_id"],
            monto=d["monto"],
            sello_tiempo=d["sello_tiempo"],
            canal=d.get("canal", "fisico"),
        )
