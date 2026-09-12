# Fase 2 — Definición de requisitos del sistema distribuido

**Proyecto:** Tejiendo redes: Arquitectura de software entre hilos y nodos
**Sistema:** Red Distribuida de Puntos de Venta (RDPV) — canal físico del operador GANA
**Curso:** Arquitectura de Software — Unidad 2, Actividad 4
**Autor:** Esteban Sánchez Viana

---

## 1. Delimitación del sistema distribuido

La Unidad 1 dejó documentada la arquitectura completa del operador: veinte requisitos funcionales, catorce no funcionales y ocho patrones de diseño con su trazabilidad. Este mini proyecto no repite ese trabajo. Toma de él un subsistema concreto y lo lleva al terreno de lo distribuido, que es lo que la Unidad 2 exige demostrar.

El subsistema elegido es la **red de puntos de venta durante el cierre de un sorteo**. Se escogió por tres razones. La primera es que allí conviven nodos físicamente separados, con conectividad intermitente, lo cual es la definición práctica de un sistema distribuido y no una simulación forzada. La segunda es que cada punto de venta atiende varios apostadores a la vez, así que el manejo de hilos aparece de forma natural y no como un adorno. Y la tercera es que el cierre de sorteo concentra el pico de carga del negocio, o sea, es justo el momento donde la escalabilidad y la robustez se pueden medir en lugar de afirmarse.

### Nodos que componen el sistema

| Nodo | Cardinalidad | Responsabilidad |
|---|---|---|
| Coordinador | 1 | Registro de nodos, sello de cierre de sorteo, consolidación del estado global |
| Punto de venta (PDV) | N (configurable) | Recepción concurrente de apuestas, control de cupo local, bitácora de salida |
| Bus de eventos | 1 | Cola persistente que desacopla el registro de la liquidación |
| Liquidador | M (configurable) | Consumo concurrente de eventos, cálculo y acreditación de premios |
| Monitor | 1 | Recolección de métricas de latencia, throughput y estado de los nodos |

---

## 2. Requisitos funcionales distribuidos

Se identifican con el prefijo **RD-F** para distinguirlos de los RF de la Unidad 1. La prioridad usa el método MoSCoW, igual que en el trabajo anterior.

| ID | Requisito | Prioridad |
|---|---|---|
| RD-F01 | Registrar cada nodo de punto de venta ante el coordinador al iniciar y mantener la afiliación mediante latidos periódicos | Obligatorio |
| RD-F02 | Detectar la caída o desconexión de un nodo por ausencia de latidos y marcarlo como no disponible | Obligatorio |
| RD-F03 | Atender varias solicitudes de apuesta de forma concurrente en un mismo nodo mediante un conjunto de hilos trabajadores | Obligatorio |
| RD-F04 | Descontar el cupo disponible del punto de venta bajo exclusión mutua entre los hilos del nodo | Obligatorio |
| RD-F05 | Enviar cada apuesta al coordinador acompañada de una clave de idempotencia generada en el nodo de origen | Obligatorio |
| RD-F06 | Registrar la apuesta en una bitácora de salida local cuando el coordinador resulte inalcanzable | Obligatorio |
| RD-F07 | Continuar recibiendo apuestas mientras el nodo permanece sin conexión con el coordinador | Obligatorio |
| RD-F08 | Sincronizar la bitácora de salida al restablecerse la conexión, respetando el orden de generación | Obligatorio |
| RD-F09 | Reconocer las claves de idempotencia repetidas y devolver el resultado original en lugar de crear una apuesta nueva | Obligatorio |
| RD-F10 | Difundir el evento de cierre de sorteo desde el coordinador hacia todos los nodos suscritos | Obligatorio |
| RD-F11 | Rechazar toda apuesta cuyo sello de tiempo sea posterior al cierre difundido | Obligatorio |
| RD-F12 | Publicar en la cola de eventos cada apuesta confirmada, para su liquidación posterior | Obligatorio |
| RD-F13 | Consumir la cola de eventos mediante varios liquidadores concurrentes sin procesar dos veces el mismo evento | Obligatorio |
| RD-F14 | Emitir un evento de compensación que revierta la reserva de cupo cuando un paso posterior de la operación falle | Obligatorio |
| RD-F15 | Interrumpir las llamadas hacia un nodo o servicio que supere el umbral de fallos y responder de inmediato con degradación controlada | Obligatorio |
| RD-F16 | Consolidar y exponer el estado global de la red: nodos activos, apuestas registradas y pendientes de sincronizar | Recomendable |
| RD-F17 | Registrar por nodo las métricas de latencia, throughput y errores durante toda la corrida | Recomendable |
| RD-F18 | Permitir la incorporación de nodos adicionales en caliente, sin detener los que ya están operando | Recomendable |
| RD-F19 | Provocar fallos y particiones de red de forma deliberada para efectos de demostración y prueba | Recomendable |

*Nota.* Elaboración propia. RD-F19 no es un requisito del negocio sino del ejercicio académico: sin la capacidad de romper el sistema a voluntad no habría forma de evidenciar la robustez durante la sustentación.

---

## 3. Requisitos no funcionales distribuidos y sus métricas

Cada requisito lleva una métrica verificable. El criterio se mantiene desde la Unidad 1: un requisito sin métrica no se puede comprobar ni discutir, y en esta actividad además es lo que la fase de evaluación va a medir.

| ID | Categoría | Requisito | Métrica de verificación |
|---|---|---|---|
| RD-NF01 | Rendimiento | Latencia de registro de una apuesta en el nodo de punto de venta | Percentil 95 menor o igual a 300 ms bajo carga nominal |
| RD-NF02 | Escalabilidad horizontal | Crecimiento del throughput al agregar nodos de punto de venta | Incremento no menor al 70 % del ideal lineal al pasar de 1 a 4 nodos |
| RD-NF03 | Escalabilidad vertical | Aprovechamiento del conjunto de hilos dentro de un nodo | Punto de saturación identificado y documentado en número de hilos |
| RD-NF04 | Concurrencia | Integridad del cupo del punto de venta bajo acceso simultáneo | Cero sobregiros de cupo en 10.000 apuestas concurrentes |
| RD-NF05 | Tolerancia a particiones | Continuidad de la operación del nodo sin conexión al coordinador | Cero apuestas rechazadas por causa de la desconexión |
| RD-NF06 | Consistencia eventual | Convergencia del estado tras restablecer la conexión | Cero pérdidas y cero duplicados al sincronizar la bitácora de salida |
| RD-NF07 | Recuperación | Tiempo de sincronización de un nodo que vuelve en línea | Menor a 5 segundos para 500 apuestas acumuladas |
| RD-NF08 | Detección de fallos | Latencia en detectar un nodo caído | Menor o igual a 3 latidos perdidos |
| RD-NF09 | Aislamiento de fallos | Efecto de la caída de un nodo sobre el resto de la red | Ninguna degradación medible en los nodos restantes |
| RD-NF10 | Robustez | Comportamiento ante un servicio dependiente degradado | Apertura del circuito antes de agotar el conjunto de conexiones |
| RD-NF11 | Orden y coherencia temporal | Efectividad del corte por cierre de sorteo | Cero apuestas admitidas después del sello de cierre |
| RD-NF12 | Observabilidad | Cobertura de la instrumentación | 100 % de los nodos reportando métricas al monitor |
| RD-NF13 | Reproducibilidad | Puesta en marcha del entorno completo | Un solo comando, sin dependencias externas de red |
| RD-NF14 | Portabilidad | Independencia del entorno de ejecución | Biblioteca estándar de Python, sin servicios propietarios |

*Nota.* Elaboración propia. Las métricas de RD-NF01 y RD-NF02 heredan los umbrales comprometidos en RNF-01 y RNF-02 de la Unidad 1, de modo que el prototipo pone a prueba lo que la propuesta original prometió.

---

## 4. Trazabilidad con los requisitos de la Unidad 1

Los requisitos distribuidos no se redactaron desde cero. Cada uno se desprende de un requisito ya documentado en la unidad anterior, y la tabla siguiente deja explícita esa correspondencia.

| Requisito distribuido | Origen en la Unidad 1 | Relación |
|---|---|---|
| RD-F03, RD-F04, RD-NF01, RD-NF03, RD-NF04 | RF-04, RNF-01 | El registro de apuestas en punto de venta se lleva al plano concurrente |
| RD-F05, RD-F06, RD-F07, RD-F08, RD-F09 | RF-06, RNF-04 | La operación sin conexión y su sincronización se implementan y se miden |
| RD-F10, RD-F11 | RF-03, RF-10 | El horario de cierre se convierte en un evento difundido a la red |
| RD-F12, RD-F13 | RF-10, RF-11 | La liquidación de premios pasa a procesamiento asíncrono concurrente |
| RD-F14 | RNF-05 | La consistencia entre servicios se resuelve por compensación |
| RD-F15, RD-NF10 | RNF-04, RF-16 | La protección ante dependencias degradadas se materializa |
| RD-F01, RD-F02, RD-F16, RD-F17, RD-NF08, RD-NF12 | RNF-11 | La observabilidad deja de ser un enunciado y se vuelve instrumentación |
| RD-F18, RD-NF02 | RNF-02 | El escalado por partes se demuestra con medición |

---

## 5. Supuestos y restricciones del ejercicio

- Las cifras, tiempos y volúmenes son un escenario académico y no corresponden a la operación real de la empresa, tal como se advirtió en el informe de la Unidad 1.
- La red se simula sobre una sola máquina: cada nodo es un proceso independiente que se comunica por sockets, lo cual conserva la separación de espacios de memoria y la posibilidad real de fallo de comunicación.
- La persistencia se resuelve con archivos locales por nodo. No se usa un motor de base de datos porque introduciría una dependencia externa y desplazaría el foco desde lo distribuido hacia lo transaccional.
- El alcance excluye la interfaz de usuario, las pasarelas de pago reales y el canal digital, que ya quedaron cubiertos conceptualmente en la Unidad 1.
