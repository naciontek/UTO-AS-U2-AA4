# RDPV — Red Distribuida de Puntos de Venta

Prototipo de la **Actividad 4 de la Unidad 2** del curso Arquitectura de Software
(Corporación Escuela Tecnológica del Oriente). Continúa el caso del operador de
juegos de suerte y azar GANA que se trabajó en la Unidad 1, y demuestra en
funcionamiento distintos patrones de diseño distribuidos.

El sistema simula una red de puntos de venta que registra apuestas de forma
concurrente, sigue vendiendo cuando se cae la conexión con el nodo central y
liquida los premios de forma asíncrona.

**Autor:** Esteban Sánchez Viana

---

## Guía de ejecución rápida

Si solo quieres comprobar que el prototipo funciona y ver los patrones en
acción, con esto basta. Toma unos diez minutos y no hay que instalar nada más
que Python.

**1.** Descarga el repositorio y descomprímelo en cualquier carpeta.

**2.** Doble clic en `1_Levantar_red.bat`. Se abre una ventana con la red
encendida. **Déjala abierta hasta el final.** Debe aparecer algo así:

```
[monitor] escuchando métricas en 127.0.0.1:9300
[bus] escuchando en 127.0.0.1:9200
[coordinador] escuchando en 127.0.0.1:9000
[nodo-1] escuchando en 127.0.0.1:9101 con 8 hilos
[coordinador] nodo registrado: nodo-1
```

**3.** Doble clic en `2_Prueba_de_carga.bat`. Manda 5000 apuestas con 100 hilos
y al terminar imprime el rendimiento. Lo que hay que ver es que las
**confirmadas sean 5000 y las perdidas 0**.

**4.** Doble clic en `3_Demo_particion_de_red.bat`. Esta es la prueba que de
verdad importa. El script te va guiando con pausas y en el camino te pide
ejecutar `4_Matar_coordinador.bat` y después `5_Reiniciar_coordinador.bat`.
Lo que se demuestra es lo siguiente:

| Momento de la demo | Qué debe pasar |
|---|---|
| Coordinador vivo | Las 300 apuestas se confirman de inmediato. |
| Coordinador caído | Las 400 apuestas **se aceptan igual**, y quedan guardadas en la bitácora local del nodo. Ninguna se pierde ni se rechaza. |
| Coordinador de vuelta | El nodo se vuelve a registrar solo y reenvía lo acumulado. La bitácora queda en **0 registros** y el coordinador reporta las apuestas **sin duplicados**. |

Eso último es la evidencia del requisito RD-NF06, que pedía cero pérdidas y
cero duplicados después de una partición de red.

**5.** Cuando termines, vuelve a la ventana de `1_Levantar_red.bat` y presiona
`Ctrl+C`. Eso detiene toda la red de forma ordenada.

Si no estás en Windows, o si prefieres ver los comandos por dentro, las
secciones 3 y 4 traen lo mismo paso a paso. Y si algo falla, la sección 8 tiene
la lista de errores típicos con su causa.

---

## 1. Qué se necesita

Solo **Python 3.11 o superior**. El prototipo usa únicamente la biblioteca
estándar, así que no hay que instalar dependencias ni configurar nada.

Para comprobar la versión instalada:

```
python --version
```

Si el comando no se reconoce, prueba con `py --version`. En ese caso, sustituye
`python` por `py` en todos los comandos que siguen.

> `matplotlib` solo hace falta si se quieren **regenerar** las gráficas del
> proyecto. Las gráficas ya están en `resultados/`, así que no es necesario.

---

## 2. Ejecución rápida en Windows (recomendada)

En la raíz del proyecto hay cinco archivos `.bat`. Se ejecutan con doble clic y
cada uno explica en pantalla lo que va a hacer antes de empezar.

| Archivo | Para qué sirve |
|---|---|
| `1_Levantar_red.bat` | Enciende toda la red distribuida. **Deja esta ventana abierta.** |
| `2_Prueba_de_carga.bat` | Lanza 5000 apuestas con 100 hilos y mide el rendimiento. |
| `3_Demo_particion_de_red.bat` | Guía la demostración de tolerancia a fallos, paso a paso. |
| `4_Matar_coordinador.bat` | Detiene solo el coordinador, sin tumbar el resto de la red. |
| `5_Reiniciar_coordinador.bat` | Vuelve a levantar el coordinador. |

El orden normal es 1, luego 2. Para la demostración de fallos se usa el 3, que
en su momento pide ejecutar el 4 y después el 5.

Todos se ubican solos en la carpeta correcta, así que no importa desde dónde se
abran.

---

## 3. Ejecución manual (Windows, macOS o Linux)

Abre una terminal **dentro de la carpeta del proyecto** (la que contiene
`levantar.py`) y ejecuta:

```
python levantar.py --nodos 4 --liquidadores 2 --hilos-por-nodo 8 --cupo-por-nodo 5000000000
```

Esto arranca nueve procesos independientes del sistema operativo:

| Proceso | Cantidad | Puerto |
|---|---|---|
| Coordinador | 1 | 9000 (TCP) |
| Bus de eventos | 1 | 9200 (TCP) |
| Monitor de métricas | 1 | 9300 (UDP) |
| Nodo de punto de venta | 4 | 9101, 9102, 9103, 9104 (TCP) |
| Liquidador | 2 | — |

**Deja esa terminal abierta.** `Ctrl+C` detiene toda la red de forma ordenada.

En pantalla deben aparecer líneas como estas, que confirman que la red quedó
operando:

```
[coordinador] escuchando en 127.0.0.1:9000
[coordinador] nodo registrado: nodo-1
[nodo-1] escuchando en 127.0.0.1:9101 con 8 hilos
```

### Generar carga

En una **segunda** terminal, también dentro de la carpeta del proyecto:

```
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 127.0.0.1:9102 127.0.0.1:9103 127.0.0.1:9104 --total 5000 --hilos-cliente 100
```

Al terminar imprime un resumen con las apuestas confirmadas, el throughput en
apuestas por segundo y la latencia promedio y percentil 95.

### Consultar el estado del coordinador

```
python -c "from rdpv.comun.protocolo import enviar_y_recibir; import json; print(json.dumps(enviar_y_recibir('127.0.0.1', 9000, {'tipo':'ESTADO'}), indent=2))"
```

Devuelve las apuestas confirmadas, rechazadas y duplicadas, las compensaciones
aplicadas y qué nodos están vivos.

---

## 4. Demostración de tolerancia a fallos

Es la prueba más importante, ya que es donde se ven trabajando el Outbox y el
Circuit Breaker. La idea es matar el coordinador mientras la red sigue
recibiendo apuestas, y comprobar que no se pierde ninguna.

**Paso 1.** Con la red levantada, envía 300 apuestas a un nodo para verificar
que todo funciona:

```
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 --total 300 --hilos-cliente 20
```

**Paso 2.** Detén **solo** el coordinador, sin tumbar el resto de la red. En
Windows basta con ejecutar `4_Matar_coordinador.bat`, que por dentro hace esto:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*rdpv.coordinador*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

En macOS o Linux:

```
pkill -f rdpv.coordinador
```

> No uses `Ctrl+C` en la ventana donde levantaste la red, ya que eso detiene
> todos los procesos y no solo el coordinador.

**Paso 3.** Envía 400 apuestas más, ahora con el coordinador caído:

```
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 --total 400 --hilos-cliente 20
```

Deben aceptarse **las 400**. El nodo detecta que el coordinador no responde,
abre el circuito y guarda cada apuesta en su bitácora local. Para comprobarlo:

```powershell
(Get-Content resultados\outbox_nodo-1.jsonl).Count
```

**Paso 4.** Vuelve a levantar el coordinador con `5_Reiniciar_coordinador.bat`,
o manualmente en una terminal nueva:

```
python -m rdpv.coordinador
```

En pocos segundos el nodo se vuelve a registrar y reenvía lo acumulado. Repite
el conteo del paso 3 y el archivo debe quedar en **0 registros**. Al consultar
el estado del coordinador, las apuestas confirmadas deben coincidir con las
enviadas, **sin duplicados**, aunque el reenvío haya ocurrido varias veces.

Eso es lo que demuestra el requisito RD-NF06: cero pérdidas y cero duplicados.

El script `pruebas/escenario_particion.py` recorre este mismo escenario de forma
guiada, con pausas entre pasos.

### Otros fallos que se pueden provocar

Para que los liquidadores fallen una parte de las veces y se dispare la
compensación de la Saga, levanta la red así:

```
python levantar.py --nodos 4 --liquidadores 2 --prob-fallo-liquidacion 0.3
```

En el estado del coordinador debe aparecer el contador `compensaciones` subiendo.

Para ver el corte por cierre de sorteo, que es el Observer distribuido:

```
python -c "from rdpv.comun.protocolo import enviar_y_recibir; print(enviar_y_recibir('127.0.0.1', 9000, {'tipo':'CERRAR'}))"
```

Después de eso, toda apuesta nueva se rechaza con el motivo `sorteo_cerrado`, y
el rechazo lo aplica cada nodo por su cuenta, sin consultar al coordinador.

---

## 5. Reproducir las mediciones

| Prueba | Comando |
|---|---|
| Escalabilidad horizontal | Levantar con `--nodos 1`, luego 2, 3 y 4, y correr el cliente de carga con 5000 apuestas y 100 hilos en cada caso |
| Punto de saturación de hilos | `python -m pruebas.escenario_saturacion` |
| Partición de red | Sección 4 de este documento |

Los resultados de las mediciones quedaron guardados en `resultados/`
como archivos JSON, junto con las gráficas en PNG. Para regenerar las gráficas:

```
pip install matplotlib
python -m pruebas.generar_graficas
```

Las cifras absolutas van a variar según el equipo, ya que todos los procesos
compiten por los mismos núcleos. Lo que debe reproducirse es la **forma** de las
curvas y, sobre todo, los resultados de las pruebas de robustez, que no dependen
del hardware.

---

## 6. Dónde está cada patrón de diseño

| Patrón | Archivo | Qué buscar | Requisito |
|---|---|---|---|
| Thread Pool | `rdpv/nodo_pdv.py` | `ThreadPoolExecutor` | RD-F03, RD-NF03 |
| Monitor / exclusión mutua | `rdpv/nodo_pdv.py` | `_cupo_lock` | RD-F04, RD-NF04 |
| Outbox | `rdpv/comun/outbox.py` | clase `Outbox` | RD-F06, RD-F08, RD-NF05 |
| Idempotency Key | `rdpv/comun/protocolo.py` y `rdpv/coordinador.py` | `nueva_clave_idempotencia`, `_on_apuesta` | RD-F05, RD-F09, RD-NF06 |
| Observer distribuido | `rdpv/coordinador.py` | `_difundir_cierre` | RD-F10, RD-F11 |
| Saga con compensación | `rdpv/liquidador.py` y `rdpv/coordinador.py` | `_on_compensar` | RD-F14 |
| Circuit Breaker | `rdpv/comun/circuito.py` | clase `CircuitBreaker` | RD-F15, RD-NF10 |
| Heartbeat | `rdpv/nodo_pdv.py` y `rdpv/coordinador.py` | `_emitir_latidos`, `_vigilar_latidos` | RD-F01, RD-F02, RD-NF08 |
| Producer–Consumer | `rdpv/bus_eventos.py` y `rdpv/liquidador.py` | cola de eventos | RD-F12, RD-F13 |
| Mediator | `rdpv/coordinador.py` | punto único de coordinación | RD-F16 |
| Conexión persistente | `rdpv/comun/protocolo.py` | `ConexionPersistente` | RD-NF01, RD-NF02 |

---

## 7. Estructura del repositorio

```
UTO-AS-U2-AA4/
├── levantar.py                  Orquestador: levanta toda la red
├── 1_Levantar_red.bat           Atajos para Windows
├── 2_Prueba_de_carga.bat
├── 3_Demo_particion_de_red.bat
├── 4_Matar_coordinador.bat
├── 5_Reiniciar_coordinador.bat
├── rdpv/
│   ├── coordinador.py           Mediator, idempotencia, cierre, heartbeat
│   ├── nodo_pdv.py              Hilos, cupo con candado, outbox, circuito
│   ├── bus_eventos.py           Cola de eventos (Producer–Consumer)
│   ├── liquidador.py            Consumidor, emite compensaciones (Saga)
│   ├── monitor.py               Recolector de métricas por UDP
│   └── comun/
│       ├── protocolo.py         Mensajes JSON, claves de idempotencia
│       ├── circuito.py          Circuit Breaker
│       ├── outbox.py            Bitácora de salida
│       └── metricas.py          Emisor de métricas
├── pruebas/
│   ├── cliente_carga.py         Generador de carga concurrente
│   ├── escenario_particion.py   Demo guiada de partición de red
│   ├── escenario_saturacion.py  Barrido de niveles de concurrencia
│   ├── generar_graficas.py      Gráficas de resultados
│   └── generar_diagramas.py     Diagramas UML del sistema
└── resultados/                  Corridas en JSON y gráficas en PNG
```

---

## 8. Si algo no funciona

| Qué aparece | Qué pasó |
|---|---|
| `No module named 'pruebas'` o `'rdpv'` | La terminal no está en la carpeta del proyecto. Ubícate en la carpeta que contiene `levantar.py`. |
| `python no se reconoce...` | Python no está en el PATH. Usa `py` en lugar de `python`. |
| `TimeoutError` o `ConnectionRefusedError` al generar carga | La red no está levantada, o el coordinador está caído. Revisa la ventana donde levantaste la red. |
| `Address already in use` | Quedaron procesos de una ejecución anterior. Ciérralos y vuelve a levantar la red. |
| La bitácora de salida no se vacía | El coordinador no volvió a arrancar. La sincronización se reintenta cada segundo, así que se vacía sola en cuanto responda. |
