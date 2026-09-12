"""
Circuit Breaker (RD-F15, RD-NF10).

Envuelve las llamadas de un nodo de punto de venta hacia el coordinador.
Si la tasa de fallos supera el umbral, el circuito se abre y las
llamadas siguientes fallan de inmediato (degradación controlada) en
lugar de agotar el conjunto de hilos del nodo esperando timeouts.

Ajustes documentados en la Unidad 1 que se conservan aquí:
- La excepción de saldo insuficiente / rechazo de negocio NO cuenta como
  fallo de infraestructura (se excluye del conteo).
- Los reintentos son seguros porque cada operación lleva una clave de
  idempotencia (no generan una segunda reserva).
"""
from __future__ import annotations

import threading
import time
from enum import Enum


class EstadoCircuito(Enum):
    CERRADO = "cerrado"
    ABIERTO = "abierto"
    SEMIABIERTO = "semiabierto"


class CircuitoAbiertoError(Exception):
    """Se lanza cuando el circuito está abierto y se rechaza la llamada de inmediato."""


class RechazoDeNegocio(Exception):
    """Marca un error de negocio (p. ej. sorteo cerrado) que NO cuenta como fallo de infraestructura."""


class CircuitBreaker:
    def __init__(self, umbral_fallos: int = 5, ventana_segundos: float = 5.0,
                 espera_reset_segundos: float = 3.0):
        self._umbral = umbral_fallos
        self._ventana = ventana_segundos
        self._espera_reset = espera_reset_segundos
        self._fallos: list[float] = []
        self._estado = EstadoCircuito.CERRADO
        self._abierto_desde: float | None = None
        self._lock = threading.Lock()
        self.aperturas_totales = 0

    @property
    def estado(self) -> EstadoCircuito:
        with self._lock:
            self._actualizar_estado()
            return self._estado

    def _actualizar_estado(self) -> None:
        if self._estado == EstadoCircuito.ABIERTO:
            if time.monotonic() - self._abierto_desde >= self._espera_reset:
                self._estado = EstadoCircuito.SEMIABIERTO

    def ejecutar(self, funcion, *args, **kwargs):
        with self._lock:
            self._actualizar_estado()
            if self._estado == EstadoCircuito.ABIERTO:
                raise CircuitoAbiertoError("Circuito abierto: se rechaza la llamada sin intentar la red")

        try:
            resultado = funcion(*args, **kwargs)
        except RechazoDeNegocio:
            # Un rechazo de negocio es una respuesta válida del sistema, no una falla.
            with self._lock:
                if self._estado == EstadoCircuito.SEMIABIERTO:
                    self._estado = EstadoCircuito.CERRADO
                    self._fallos.clear()
            raise
        except Exception:
            self._registrar_fallo()
            raise
        else:
            with self._lock:
                if self._estado == EstadoCircuito.SEMIABIERTO:
                    self._estado = EstadoCircuito.CERRADO
                self._fallos.clear()
            return resultado

    def _registrar_fallo(self) -> None:
        ahora = time.monotonic()
        with self._lock:
            self._fallos.append(ahora)
            self._fallos = [t for t in self._fallos if ahora - t <= self._ventana]
            if self._estado == EstadoCircuito.SEMIABIERTO:
                self._estado = EstadoCircuito.ABIERTO
                self._abierto_desde = ahora
                self.aperturas_totales += 1
            elif len(self._fallos) >= self._umbral and self._estado == EstadoCircuito.CERRADO:
                self._estado = EstadoCircuito.ABIERTO
                self._abierto_desde = ahora
                self.aperturas_totales += 1
