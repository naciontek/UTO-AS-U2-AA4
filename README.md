# RDPV — Red Distribuida de Puntos de Venta

Prototipo de la Actividad 4, Unidad 2, del curso Arquitectura de Software (CETO). Continúa el caso GANA de la Unidad 1 y demuestra, con un solo caso de uso de principio a fin, los patrones distribuidos justificados en la especificación de arquitectura (`02_Plan_de_Proyecto_y_Arquitectura.md`).

## Puesta en marcha (un solo comando — RD-NF13)

Requiere Python 3.11+ y solo la biblioteca estándar más `matplotlib` para las gráficas de evaluación.

```bash
pip install matplotlib --break-system-packages   # solo para regenerar gráficas
python levantar.py --nodos 4 --liquidadores 2 --hilos-por-nodo 8 --cupo-por-nodo 5000000000
```

Esto levanta, como procesos independientes: 1 coordinador (puerto 9000), 1 bus de eventos (9200), 1 monitor de métricas (UDP 9300), N nodos de punto de venta (9101, 9102, …) y M liquidadores. `Ctrl+C` detiene todo de forma ordenada.

Para generar carga contra la red:

```bash
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 127.0.0.1:9102 --total 5000 --hilos-cliente 100
```

## Mapa de patrones en el código

| Patrón | Archivo | Requisito |
|---|---|---|
| Thread Pool | `rdpv/nodo_pdv.py` (`ThreadPoolExecutor`) | RD-F03, RD-NF03 |
| Monitor / exclusión mutua | `rdpv/nodo_pdv.py` (`_cupo_lock`) | RD-F04, RD-NF04 |
| Outbox con sincronización diferida | `rdpv/comun/outbox.py` | RD-F06, RD-F08, RD-NF05 |
| Idempotency Key | `rdpv/comun/protocolo.py` (`nueva_clave_idempotencia`), `rdpv/coordinador.py` (`_on_apuesta`) | RD-F05, RD-F09, RD-NF06 |
| Observer distribuido | `rdpv/coordinador.py` (`_difundir_cierre`) | RD-F10, RD-F11 |
| Saga con compensación | `rdpv/liquidador.py`, `rdpv/coordinador.py` (`_on_compensar`) | RD-F14 |
| Circuit Breaker | `rdpv/comun/circuito.py` | RD-F15, RD-NF10 |
| Heartbeat | `rdpv/nodo_pdv.py` (`_emitir_latidos`), `rdpv/coordinador.py` (`_vigilar_latidos`) | RD-F01, RD-F02, RD-NF08 |
| Producer–Consumer | `rdpv/bus_eventos.py`, `rdpv/liquidador.py` | RD-F12, RD-F13 |
| Mediator | `rdpv/coordinador.py` (punto único de coordinación) | RD-F16 |
| Conexión persistente (ajuste de evaluación) | `rdpv/comun/protocolo.py` (`ConexionPersistente`) | RD-NF01, RD-NF02 |

## Provocar fallos para la demostración (RD-F19)

```bash
# 1. Levantar la red normalmente.
# 2. Matar el proceso del coordinador (Ctrl+C o kill) mientras un nodo sigue recibiendo carga:
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 --total 400 --hilos-cliente 20
# Las apuestas se aceptan igual (vía Outbox). Verifícalo:
wc -l resultados/outbox_nodo-1.jsonl
# 3. Reiniciar el coordinador y observar la sincronización automática:
python -m rdpv.coordinador
# El outbox se vacía en segundos, sin pérdidas ni duplicados.
```

`pruebas/escenario_particion.py` guía este mismo escenario de forma interactiva, pensado para grabarse en el video de sustentación.

## Pruebas de evaluación

- `pruebas/cliente_carga.py` — generador de carga concurrente, mide latencia y throughput.
- `pruebas/escenario_saturacion.py` — barrido de niveles de concurrencia del cliente.
- `pruebas/generar_graficas.py` — produce las gráficas de `resultados/` a partir de las corridas guardadas.

Los resultados de las corridas usadas en el informe están en `resultados/` (JSON) y sus gráficas correspondientes (PNG). El detalle completo del análisis está en el documento de evaluación de la Fase 5.

## Estructura

Ver Sección 11 de `02_Plan_de_Proyecto_y_Arquitectura.md`.

## Autor

Esteban Sánchez Viana — Corporación Escuela Tecnológica del Oriente — Arquitectura de Software, Unidad 2.
