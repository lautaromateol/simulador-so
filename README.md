# Simulador de Asignación de Memoria y Planificación de Procesos

Simulador por consola para la materia *Sistemas Operativos* (UTN FRRe - ISI). Simula hasta 10 procesos en un sistema **uniprocesador** con:

- **Memoria:** particiones variables (MVT) con política **Best-Fit**. RAM de 550K: 100K reservados al SO (0K–99K) y 450K para procesos de usuario (100K–549K).
- **Planificación:** **SRTF** (*Shortest Remaining Time First*), apropiativo.
- **Multiprogramación:** como máximo **5 procesos** entre Ejecución + Listo + Listo/Suspendido.
- **Estados:** Nuevo, Listo, Listo/Suspendido, Ejecución y Terminado (no hay Bloqueado).

## Requisitos

- Python 3.10 o superior. El simulador no usa bibliotecas externas.
- Solo para correr los tests: `pip install -r requirements-dev.txt` (pytest y ruff).

## Ejecución

```
python main.py --input <archivo>
```

| Terminal | Comando (sin activar el entorno virtual) |
|---|---|
| PowerShell / CMD | `.venv\Scripts\python main.py --input pruebas\tutorial.txt` |
| Git Bash | `.venv/Scripts/python main.py --input pruebas/tutorial.txt` |

Con el entorno virtual activado alcanza con `python main.py --input pruebas/tutorial.txt`. En Git Bash usá siempre `/`: la barra invertida `\` se interpreta como escape.

La simulación **se detiene en cada evento** (arribo o fin de un proceso) y espera **Enter** para continuar. No existe modo de corrida ininterrumpida. Al terminar muestra el informe final. `Ctrl+C` interrumpe la simulación.

## Formato del archivo de entrada

Texto plano, un proceso por línea, campos separados por comas:

```
# Id, Tamaño (K), Arribo, Irrupción
P1,120,0,8
P2,60,1,4
```

- Las líneas vacías y las que empiezan con `#` se ignoran.
- **Id:** texto no vacío y único. Los Id se ordenan de forma natural (`P2` antes que `P10`).
- **Tamaño:** entero en K, mayor que 0 y como máximo 450 (un proceso más grande nunca podría asignarse).
- **Arribo:** entero mayor o igual que 0.
- **Irrupción:** entero mayor que 0.
- Como máximo 10 procesos.

Si el archivo no existe, está vacío o tiene datos inválidos, el programa informa **todos los errores con su número de línea** y no arranca. Por ejemplo:

```
Error: Línea 3: el proceso 'P3' pide 500K y supera los 450K disponibles
Línea 4: el Id 'P1' ya fue definido en la línea 2
```

## Cómo leer la salida

Cada pausa muestra un bloque como este:

```
========== t = 1 ==========          ← instante
ARRIBO  P2                           ← eventos del instante (ARRIBO / FIN)
--------------------------
CPU: P2 (restante 2)                 ← proceso en ejecución o "CPU ociosa"
Desalojo: P1 fue desalojado por P2   ← solo si hubo desalojo
Colas:
  Listo: P1(5)                       ← (tiempo restante), en orden de prioridad SRTF
  Listo/Suspendido: (vacío)          ← admitidos sin partición, por orden de suspensión
  Nuevo: (vacío)                     ← arribados que esperan cupo
  Por arribar: P3(arribo 2), ...
  Terminados: (vacío)                ← con su instante de finalización
  Grado de multiprogramación: 2/5   (Ejecución 1 + Listo 1 + Listo/Suspendido 0)
Memoria:
 Id Inicio Tamaño Estado  Proceso    ← particiones ordenadas por dirección
  0     0K   100K OCUPADA SO
  1   100K   200K OCUPADA P1
  2   300K   150K OCUPADA P2
  3   450K   100K LIBRE   Libre
  Total: 550K  Memoria libre: 100K  Mayor hueco disponible: 100K
```

Al final se muestra el **informe**: por proceso, arribo, irrupción, finalización, Tiempo de Retorno y Tiempo de Espera, seguido de los promedios y el Throughput.

```
Retorno medio: 8.71 u.t.
Espera media: 5.43 u.t.
Throughput: 0.30 procesos/u.t. (7 procesos en 23 u.t., de t=0 a t=23)
```

## Supuestos y decisiones

1. **Admisión:** un proceso que arriba pasa a *Nuevo* y se admite solo si Ejecución + Listo + Listo/Suspendido < 5. Si hay partición Best-Fit va a *Listo*; si no hay memoria suficiente va a *Listo/Suspendido* (y ocupa cupo). Con 5 admitidos permanece en *Nuevo*. Al liberarse cupo se admite en orden de arribo.
2. **Fragmentación:** la consigna pide "fragmentación interna", pero en MVT no existe: cada partición se crea del tamaño exacto del proceso. Lo tomamos como un error de la consigna y mostramos la **fragmentación externa**: los huecos libres en la tabla, el total libre y el mayor hueco. No se implementa compactación.
3. **Best-Fit:** se elige el hueco libre más chico que contenga al proceso; ante empate, el de menor dirección. El sobrante queda como un hueco nuevo. Al liberar, la partición se une con los huecos libres adyacentes (anterior, posterior o ambos). La partición del SO nunca se libera ni se une.
4. **Estados:** Nuevo, Listo, Listo/Suspendido, Ejecución y Terminado. Una transición no permitida es un error interno del simulador.
5. **Tiempos:** Retorno = finalización − arribo. Espera = Retorno − irrupción.
6. **SRTF:** se ejecuta el de menor tiempo restante; empates por menor arribo y luego menor Id. Un proceso con tiempo restante **igual** al del que está en ejecución **no** lo desaloja (solo si es estrictamente menor).
7. **Reactivación de Listo/Suspendido:** en orden de suspensión (FIFO), probando cada proceso; uno que no entra no bloquea a los siguientes. *Pendiente de confirmar con la cátedra.*
8. **Throughput:** procesos terminados / (finalización del último − menor arribo). No cuenta el tiempo previo al primer arribo. *Pendiente de confirmar con la cátedra.*
9. **Salida:** se muestra un bloque en cada arribo y en cada fin de proceso. Los eventos del mismo instante se agrupan en un solo bloque.

## Orden de los eventos simultáneos

Cuando en un mismo instante `t` ocurren varias cosas, se procesan siempre en este orden:

1. **Fin** del proceso en ejecución y liberación (y unión) de su memoria.
2. **Reactivación** de procesos en Listo/Suspendido que ahora tengan partición.
3. **Arribos** del instante (por Id ascendente) y **admisión** desde Nuevo mientras haya cupo.
4. **Selección SRTF:** desalojo si corresponde y asignación de la CPU.

Así la simulación es determinista: el mismo archivo produce siempre la misma salida.

## Casos de prueba

Cada archivo de `pruebas/` tiene su salida esperada **calculada a mano** en `pruebas/esperado/` (diagrama de CPU, eventos clave e informe final). El test `tests/test_casos.py` verifica que el simulador coincida con todas.

| Archivo | Qué ejercita |
|---|---|
| `01_basico.txt` | 3 procesos sin desalojo ni falta de memoria; un tramo de CPU ociosa. |
| `02_desalojo_srtf.txt` | Caso clásico de libro: desalojo SRTF, espera media 6.50. |
| `03_limite_5.txt` | 7 procesos en t=0: P6 y P7 esperan en Nuevo con el cupo lleno. |
| `04_listo_suspendido.txt` | Un proceso de 250K espera en Listo/Suspendido hasta que se unen dos huecos. |
| `10_procesos.txt` | Caso integral: desalojo, 4 suspensiones, cupo lleno, Best-Fit y unión de huecos. |
| `tutorial.txt` | Recorrido didáctico de todas las reglas, incluido un empate SRTF. |

## Tests

```
python -m pytest -q
python -m ruff check .
```

## Estructura

```
main.py                    Punto de entrada (lectura de argumentos)
simulador/
  lectura.py               Lectura y validación del archivo de procesos
  pcb.py                   PCB, estados, transiciones válidas y colas
  memoria.py               Memoria MVT: Best-Fit, liberación y unión de huecos
  motor.py                 Reloj, eventos, admisión y límite de multiprogramación
  planificador.py          Política SRTF
  reporte.py               Salida por evento, informe final y métricas
pruebas/                   Archivos de entrada
pruebas/esperado/          Salidas esperadas calculadas a mano
tests/                     Tests automáticos (pytest)
```
