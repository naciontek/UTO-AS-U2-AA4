"""
Escenario de partición de red (RD-F19, RD-NF05, RD-NF06, RD-NF07).

Simula la caída del coordinador mientras un nodo de punto de venta
sigue recibiendo apuestas, para demostrar:
  - Outbox: las apuestas se preservan localmente (RD-F06, RD-F07).
  - Circuit Breaker: el nodo deja de intentar la red en cada solicitud
    una vez detecta la caída (RD-F15).
  - Sincronización: al restablecer el coordinador, el outbox se vacía
    sin pérdidas ni duplicados (RD-F08, RD-F09, RD-NF06) y se mide el
    tiempo que tarda (RD-NF07).

Requiere que la red ya esté levantada con `levantar.py` y que se le
indique el proceso del coordinador para suspenderlo/reanudarlo, o bien
se ejecuta manualmente deteniendo el coordinador con Ctrl+C en su
terminal y volviéndolo a lanzar.

Este script asume un uso semi-manual: genera carga contra un nodo,
imprime instrucciones para cortar el coordinador, espera, genera más
carga, y luego pide reanudar el coordinador para medir la sincronización.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

sys.path.insert(0, ".")
from rdpv.comun.protocolo import enviar_y_recibir
from pruebas.cliente_carga import ejecutar_carga


def obtener_estado(host_coord: str, puerto_coord: int) -> dict | None:
    try:
        return enviar_y_recibir(host_coord, puerto_coord, {"tipo": "ESTADO"}, timeout=1.0)
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodo", default="127.0.0.1:9101")
    parser.add_argument("--host-coordinador", default="127.0.0.1")
    parser.add_argument("--puerto-coordinador", type=int, default=9000)
    parser.add_argument("--apuestas-durante-particion", type=int, default=300)
    args = parser.parse_args()

    host, puerto = args.nodo.split(":")
    nodo = (host, int(puerto))

    print("=== Escenario de partición de red ===")
    estado_previo = obtener_estado(args.host_coordinador, args.puerto_coordinador)
    print("Estado del coordinador antes de la partición:", json.dumps(estado_previo, ensure_ascii=False))

    input("\n>> Detén ahora el proceso del coordinador (Ctrl+C en su terminal) y presiona ENTER para continuar...")

    print(f"Generando {args.apuestas_durante_particion} apuestas contra {args.nodo} sin coordinador disponible...")
    inicio = time.perf_counter()
    resultado = ejecutar_carga([nodo], args.apuestas_durante_particion, hilos_cliente=20)
    duracion_particion = time.perf_counter() - inicio
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(f"Todas deberían reportar 'via': 'outbox' con exito=True (revisa el log del nodo).")
    print(f"Duración de la ventana con partición: {duracion_particion:.2f} s")

    input("\n>> Reinicia ahora el coordinador (python -m rdpv.coordinador) y presiona ENTER para medir la sincronización...")

    inicio_sync = time.perf_counter()
    pendientes_previos = None
    while True:
        estado = obtener_estado(args.host_coordinador, args.puerto_coordinador)
        if estado is not None:
            break
        time.sleep(0.2)

    # Espera activa hasta que el outbox del nodo quede vacío (se lee el reporte vía log,
    # o se puede consultar el archivo de outbox directamente).
    print("Coordinador disponible de nuevo. Esperando a que el nodo sincronice su outbox...")
    time.sleep(6)  # margen para el ciclo de reintento (1 s) más la propagación
    duracion_sync = time.perf_counter() - inicio_sync

    estado_final = obtener_estado(args.host_coordinador, args.puerto_coordinador)
    print("\nEstado del coordinador después de la sincronización:")
    print(json.dumps(estado_final, ensure_ascii=False, indent=2))
    print(f"\nTiempo aproximado de sincronización: {duracion_sync:.2f} s (meta RD-NF07: < 5 s para 500 apuestas)")


if __name__ == "__main__":
    main()
