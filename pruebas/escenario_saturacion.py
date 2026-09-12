"""
Escenario de saturación de hilos (RD-NF03) y de escalado horizontal
(RD-NF02).

Requiere que la red ya esté levantada. Corre la misma carga contra un
solo nodo variando el número de hilos configurado en ese nodo NO es
posible sin reiniciarlo, así que este script asume que se reinicia el
nodo objetivo entre corridas con --hilos distinto (ver README para el
procedimiento exacto), o bien mide el efecto indirectamente por medio
del throughput con distinto número de hilos-cliente concurrentes
contra un número fijo de nodos, que es lo que permite observar el
punto de saturación sin reiniciar procesos.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, ".")
from pruebas.cliente_carga import ejecutar_carga


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodos", nargs="+", required=True)
    parser.add_argument("--total-por-corrida", type=int, default=1500)
    parser.add_argument("--niveles-hilos-cliente", nargs="+", type=int,
                         default=[5, 10, 20, 40, 80, 160, 320])
    parser.add_argument("--salida", default="resultados/saturacion.json")
    args = parser.parse_args()

    nodos = []
    for n in args.nodos:
        host, puerto = n.split(":")
        nodos.append((host, int(puerto)))

    resultados = []
    for hilos in args.niveles_hilos_cliente:
        print(f"--- corriendo con {hilos} hilos de cliente concurrentes ---")
        r = ejecutar_carga(nodos, args.total_por_corrida, hilos)
        r["hilos_cliente_nivel"] = hilos
        resultados.append(r)
        print(json.dumps(r, ensure_ascii=False, indent=2))

    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en {args.salida}")


if __name__ == "__main__":
    main()
