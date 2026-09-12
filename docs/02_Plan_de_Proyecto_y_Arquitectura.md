# Fase 3 — Plan de proyecto y especificación de la arquitectura

**Proyecto:** Tejiendo redes: Arquitectura de software entre hilos y nodos
**Sistema:** Red Distribuida de Puntos de Venta (RDPV) — canal físico del operador GANA
**Curso:** Arquitectura de Software — Unidad 2, Actividad 4
**Autor:** Esteban Sánchez Viana

---

# PARTE I — PLAN DE PROYECTO

## 1. Objetivos

### Objetivo general

Diseñar, implementar y evaluar una arquitectura de software distribuida para la red de puntos de venta del operador GANA, aplicando patrones de diseño pertinentes y modelado UML, de modo que se pueda verificar con métricas su comportamiento frente a la concurrencia, la partición de red y el crecimiento de la carga.

### Objetivos específicos

1. Especificar los requisitos funcionales y no funcionales propios del comportamiento distribuido, asignando a cada uno una métrica verificable.
2. Definir la descomposición en nodos y los contratos de comunicación entre ellos, antes de escribir la primera línea de código.
3. Implementar un prototipo funcional en el que los nodos operen como procesos independientes y cada nodo atienda solicitudes concurrentes mediante un conjunto de hilos.
4. Seleccionar y justificar los patrones de diseño aplicados, estableciendo para cada uno la falla concreta que se produciría en su ausencia.
5. Ejecutar pruebas de escalabilidad y robustez que arrojen métricas observadas, identificar el cuello de botella predominante y aplicar al menos un ajuste con medición antes y después.
6. Documentar la arquitectura resultante mediante diagramas de componentes, secuencia y despliegue fieles a la implementación.

## 2. Metas del sistema

Las metas traducen los objetivos a resultados comprobables sobre el prototipo. No son aspiraciones: cada una se declara aprobada o reprobada en la fase de evaluación.

| Meta | Criterio de aprobación | Requisito asociado |
|---|---|---|
| M1. Concurrencia segura | Cero sobregiros de cupo con múltiples hilos compitiendo | RD-NF04 |
| M2. Respuesta bajo carga | Percentil 95 de latencia menor o igual a 300 ms en carga nominal | RD-NF01 |
| M3. Escalado horizontal | Al menos 70 % del incremento lineal ideal al pasar de 1 a 4 nodos | RD-NF02 |
| M4. Continuidad ante partición | Cero apuestas rechazadas mientras un nodo permanece desconectado | RD-NF05 |
| M5. Convergencia | Cero pérdidas y cero duplicados al sincronizar | RD-NF06 |
| M6. Aislamiento | La caída de un nodo no degrada de forma medible a los demás | RD-NF09 |
| M7. Corte temporal exacto | Cero apuestas admitidas después del sello de cierre | RD-NF11 |

## 3. Relevancia de la comunicación entre nodos e hilos

Conviene separar los dos planos, porque son problemas distintos y se resuelven con mecanismos distintos, aunque la actividad los nombre juntos.

**Entre hilos**, dentro de un mismo nodo, el problema es la memoria compartida. Varios hilos del punto de venta tocan el mismo contador de cupo, y sin exclusión mutua dos apuestas simultáneas pueden leer el mismo saldo disponible y descontarlo dos veces sobre la misma base. Eso produce un sobregiro que no se manifiesta como error sino como un número equivocado, o sea, el peor tipo de falla: silenciosa. Aquí la comunicación es implícita, ocurre a través del estado, y el costo de coordinar es un bloqueo que reduce el paralelismo. De ahí que el tamaño del conjunto de hilos no sea un número que se elija al azar: por debajo se desaprovecha la máquina y por encima los hilos pasan más tiempo esperando el candado que trabajando. Ese punto de saturación es una de las cosas que el prototipo debe encontrar de forma empírica.

**Entre nodos**, en cambio, no hay memoria compartida y la comunicación es explícita: un mensaje que viaja por la red y que puede perderse, llegar tarde, llegar dos veces o no llegar nunca. La diferencia de fondo es que un hilo bloqueado eventualmente avanza, mientras que un nodo que no responde es indistinguible de un nodo lento. Por eso los mecanismos cambian por completo: se necesita idempotencia, porque el reenvío es inevitable; se necesita detección por latidos, porque el silencio hay que interpretarlo; y se necesita compensación en lugar de reversión, porque no existe una transacción que abarque a los dos extremos.

Esa distinción es la que ordena todo el diseño que sigue. Dentro del nodo se usa un candado. Entre nodos se usan mensajes idempotentes y compensación.

## 4. Estrategia de trabajo y roles

La entrega es individual, así que los roles que la guía plantea para un equipo se asumen de forma secuencial por una sola persona. Se documentan igual, porque cada rol implica un criterio de decisión distinto y forzar el cambio de sombrero evita que el diseño y su evaluación se hagan con la misma mirada complaciente.

| Rol | Responsabilidad asumida | Producto asociado |
|---|---|---|
| Líder de proyecto | Alcance, cronograma y verificación final contra la rúbrica | Plan de proyecto, autoevaluación |
| Analista de requisitos | Levantamiento, priorización MoSCoW y definición de métricas | Documento de requisitos |
| Diseñador de arquitectura | Descomposición en nodos, contratos y selección de patrones | Especificación y diagramas UML |
| Desarrollador | Implementación de coordinador, nodos, bus y liquidadores | Prototipo y repositorio |
| Evaluador de calidad | Pruebas de carga y robustez, análisis de cuellos de botella | Informe de evaluación |
| Documentador | Redacción en APA 7, presentación y guion | Informe, PPTX y libreto |

Como evidencia del trabajo organizado se llevará una bitácora de decisiones y el historial de commits fechados del repositorio, que sustituye a la evidencia de colaboración que la rúbrica espera de un grupo.

## 5. Cronograma

| # | Actividad | Fechas | Estado |
|---|---|---|---|
| 1 | Análisis de la guía, la rúbrica y el trabajo previo | 12 sep | Completada |
| 2 | Definición de requisitos y métricas | 12 sep | Completada |
| 3 | Plan de proyecto y especificación de la arquitectura | 12 sep | En curso |
| 4 | Implementación del prototipo distribuido | 13 – 16 sep | Pendiente |
| 5 | Pruebas de carga, robustez y ajustes | 17 – 18 sep | Pendiente |
| 6 | Diagramas UML a partir de la implementación | 19 sep | Pendiente |
| 7 | Redacción del informe en APA 7 | 20 – 22 sep | Pendiente |
| 8 | Presentación y guion | 23 – 24 sep | Pendiente |
| 9 | Grabación, publicación del video y del repositorio | 25 sep | Pendiente |
| 10 | Verificación final contra la rúbrica y entrega | 26 sep | Pendiente |

## 6. Herramientas

| Herramienta | Uso | Justificación |
|---|---|---|
| Python 3.11, biblioteca estándar | Nodos, hilos, sockets y colas | Sin dependencias externas: el evaluador levanta el entorno con un comando |
| Módulo `threading` | Conjuntos de hilos, candados y eventos | Expone de forma explícita los mecanismos de concurrencia que el ejercicio debe evidenciar |
| Módulo `socket` sobre TCP | Comunicación entre nodos | Conserva el fallo de red real; una llamada en memoria no se puede interrumpir de forma creíble |
| Archivos JSON por nodo | Bitácora de salida y persistencia local | Mantiene el foco en lo distribuido y no en lo transaccional |
| `matplotlib` | Gráficas de las métricas obtenidas | Convierte los resultados de las pruebas en evidencia visual para el informe |
| Git y GitHub | Control de versiones y entrega del código | Historial fechado como evidencia de proceso |
| PlantUML / Graphviz | Renderizado de los diagramas UML | Diagramas versionables como texto, regenerables si el diseño cambia |
| Microsoft PowerPoint | Presentación | Coherencia con el sistema visual de los entregables anteriores |

---

# PARTE II — ESPECIFICACIÓN DE LA ARQUITECTURA

Esta sección es el plano de trabajo del prototipo. Los diagramas UML se generarán después, a partir de lo implementado, para garantizar que documento y código coincidan.

## 7. Inventario de componentes

| Componente | Proceso | Puerto | Responsabilidad | Concurrencia interna |
|---|---|---|---|---|
| `coordinador` | 1 | 9000 | Registro de nodos, validación de idempotencia, sello de cierre, estado global | Conjunto de hilos aceptadores + hilo vigilante de latidos |
| `nodo_pdv` | N | 9101 – 91NN | Recepción de apuestas, control de cupo, bitácora de salida, sincronización | Conjunto de hilos trabajadores + hilo de reintento + hilo de latido |
| `bus_eventos` | 1 | 9200 | Cola persistente de eventos confirmados, entrega en exclusiva a los consumidores | Un hilo por consumidor conectado |
| `liquidador` | M | — | Consumo de eventos, cálculo del premio, emisión de compensaciones | Un hilo consumidor por instancia |
| `monitor` | 1 | 9300 | Recolección de métricas, estado de la red, exportación de resultados | Hilo receptor + hilo de agregación |
| `cliente_carga` | 1 | — | Generador de apuestas para las pruebas de escalabilidad | Conjunto de hilos generadores configurable |

## 8. Contratos de comunicación

El transporte es TCP con mensajes JSON delimitados por salto de línea. Se eligió un protocolo de texto porque permite inspeccionar el tráfico durante la sustentación, lo cual tiene valor demostrativo.

| Mensaje | Origen → Destino | Campos principales | Respuesta esperada |
|---|---|---|---|
| `REGISTRO` | PDV → Coordinador | `nodo_id`, `puerto`, `cupo_inicial` | `OK` con el estado del sorteo vigente |
| `LATIDO` | PDV → Coordinador | `nodo_id`, `secuencia`, `pendientes` | `OK` o `CIERRE` si el sorteo ya cerró |
| `APUESTA` | PDV → Coordinador | `clave_idem`, `nodo_id`, `monto`, `sello_tiempo` | `CONFIRMADA`, `DUPLICADA` o `RECHAZADA` |
| `SINCRONIZAR` | PDV → Coordinador | Lote ordenado de apuestas de la bitácora | Resultado individual por clave de idempotencia |
| `CIERRE` | Coordinador → PDV | `sorteo_id`, `sello_cierre` | Confirmación de recepción |
| `PUBLICAR` | Coordinador → Bus | `evento`, `carga_util` | `ENCOLADO` |
| `CONSUMIR` | Liquidador → Bus | `consumidor_id` | Evento o `VACIO` |
| `COMPENSAR` | Liquidador → Coordinador | `clave_idem`, `motivo` | `REVERTIDA` |
| `METRICA` | Todos → Monitor | `nodo_id`, `tipo`, `valor`, `sello_tiempo` | Sin respuesta (envío asíncrono) |

## 9. Flujo del caso crítico: registro de una apuesta

1. El cliente de carga envía una solicitud de apuesta al nodo de punto de venta.
2. Un hilo trabajador libre del conjunto la toma. Si no hay ninguno disponible, la solicitud espera en la cola de entrada del nodo, y ese tiempo de espera se contabiliza dentro de la latencia.
3. El hilo genera la clave de idempotencia y solicita el candado del cupo.
4. Con el candado tomado, verifica y descuenta el cupo. La sección crítica se mantiene mínima a propósito: solo el descuento, nada de entrada o salida.
5. El hilo intenta enviar el mensaje `APUESTA` al coordinador.
   - **Camino normal:** el coordinador verifica que la clave no exista, valida el sello contra el cierre, registra y responde `CONFIRMADA`. El coordinador publica el evento en el bus. El nodo responde al cliente.
   - **Camino sin conexión:** el envío falla. El nodo escribe la apuesta en la bitácora de salida, responde al cliente como aceptada de forma provisional, y el hilo de reintento se encarga después. El cupo ya fue descontado localmente, así que la operación es coherente desde la perspectiva del punto de venta.
   - **Camino de rechazo:** el coordinador responde `RECHAZADA` porque el sorteo cerró. El hilo devuelve el cupo descontado bajo el mismo candado y responde el rechazo al cliente.
6. Al restablecerse la conexión, el hilo de reintento envía la bitácora completa mediante `SINCRONIZAR`, en el orden en que fue generada. El coordinador responde por cada clave si quedó confirmada o si ya existía. Las duplicadas se descartan sin efecto.
7. Un liquidador toma el evento del bus, calcula el premio y acredita. Si esa acreditación falla, emite `COMPENSAR` y el coordinador revierte la reserva asociada.

## 10. Mapa de patrones sobre los componentes

Se conserva el criterio de la Unidad 1: cada patrón debe resolver un requisito documentado, y para cada uno se enuncia la falla que ocurriría en su ausencia. Los patrones marcados como heredados ya fueron justificados en el trabajo anterior y aquí pasan de la propuesta a la implementación.

| Patrón | Dónde vive | Falla que evita | Requisito | Origen |
|---|---|---|---|---|
| Thread Pool | `nodo_pdv`, `coordinador` | Crear un hilo por solicitud agota la memoria en el pico de cierre | RD-F03, RD-NF03 | Nuevo |
| Monitor / exclusión mutua | Candado de cupo en `nodo_pdv` | Dos hilos descuentan sobre el mismo saldo leído y se sobregira el cupo | RD-F04, RD-NF04 | Nuevo |
| Outbox con sincronización diferida | Bitácora local de `nodo_pdv` | El punto de venta queda inservible al perder la conexión | RD-F06, RD-F08, RD-NF05 | Heredado |
| Idempotency Key | Clave generada en `nodo_pdv`, verificada en `coordinador` | El reenvío tras la reconexión crea apuestas duplicadas | RD-F05, RD-F09, RD-NF06 | Heredado |
| Observer distribuido | Difusión de `CIERRE` a los nodos suscritos | Cada nodo consulta el estado del sorteo y satura al coordinador | RD-F10, RD-F11 | Nuevo |
| Saga con compensación | `liquidador` y `coordinador` | Queda cupo comprometido sin apuesta asociada cuando falla un paso | RD-F14 | Heredado |
| Circuit Breaker | Cliente del `coordinador` dentro de `nodo_pdv` | Un coordinador lento agota los hilos del nodo y tumba también lo local | RD-F15, RD-NF10 | Heredado |
| Heartbeat | `nodo_pdv` hacia `coordinador` | Un nodo caído se confunde con uno lento y nadie lo detecta | RD-F01, RD-F02, RD-NF08 | Nuevo |
| Producer–Consumer | `bus_eventos` y `liquidador` | La liquidación bloquea el registro de apuestas en el momento de mayor carga | RD-F12, RD-F13 | Nuevo |
| Mediator | `coordinador` como punto único de coordinación | Los nodos se comunican entre sí y las rutas crecen de forma cuadrática | RD-F16 | Nuevo |

## 11. Estructura del repositorio prevista

```
UTO-AS-U2-AA4/
├── README.md                  Instrucciones, mapa de patrones y resultados
├── rdpv/
│   ├── coordinador.py
│   ├── nodo_pdv.py
│   ├── bus_eventos.py
│   ├── liquidador.py
│   ├── monitor.py
│   └── comun/
│       ├── protocolo.py       Serialización y contratos de mensaje
│       ├── circuito.py        Circuit Breaker
│       ├── outbox.py          Bitácora de salida
│       └── metricas.py        Instrumentación
├── pruebas/
│   ├── cliente_carga.py       Generador concurrente de apuestas
│   ├── escenario_particion.py Corte y restablecimiento de red
│   └── escenario_saturacion.py Barrido del número de hilos
├── resultados/                Métricas y gráficas de cada corrida
└── levantar.py                Puesta en marcha de la red completa
```
