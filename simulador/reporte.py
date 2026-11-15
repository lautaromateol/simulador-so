from collections.abc import Callable
from dataclasses import dataclass

from simulador.memoria import ID_SO, EstadoParticion
from simulador.motor import GRADO_MAXIMO, Evento, Motor, TipoEvento
from simulador.pcb import PCB
from simulador.planificador import clave_srtf

EVENTOS_VISIBLES = {TipoEvento.ARRIBO, TipoEvento.FIN}
NOMBRES_EVENTO = {TipoEvento.ARRIBO: "ARRIBO", TipoEvento.FIN: "FIN"}
PROMPT = "Presione Enter para continuar..."
PROMPT_FINAL = "Presione Enter para finalizar..."
ENCABEZADO_MEMORIA = {"Id", "Inicio", "Tamaño", "Estado", "Proceso", "Sobrante"}

@dataclass
class Bloque:
    tiempo: int
    eventos: tuple[Evento, ...]

VACIO = "(vacío)"

def _lista(items: list[str]) -> str:
    return ", ".join(items) or VACIO

def _cola(pcbs: list[PCB]) -> str:
    return _lista([f"{p.id}({p.restante})" for p in pcbs])

def _alinear(filas: list[tuple[str, ...]], izquierda: set[int]) -> list[str]:
    anchos = [max(len(fila[i]) for fila in filas) for i in range(len(filas[0]))]
    lineas = []
    for fila in filas:
        celdas = [
            celda.ljust(ancho) if i in izquierda else celda.rjust(ancho)
            for i, (celda, ancho) in enumerate(zip(fila, anchos))
        ]
        lineas.append(" " + " ".join(celdas).rstrip())
    return lineas

def formatear_cpu(motor: Motor) -> list[str]:
    en_cpu = motor.colas.ejecucion
    if en_cpu is None:
        lineas = ["CPU ociosa"]
    else:
        lineas = [f"CPU: {en_cpu.id} (restante {en_cpu.restante})"]
    del_instante = [e for e in motor.eventos if e.tiempo == motor.reloj]
    for posicion, evento in enumerate(del_instante):
        if evento.tipo != TipoEvento.DESALOJO:
            continue
        reemplazo = next((e.proceso for e in del_instante[posicion + 1:] if e.tipo == TipoEvento.INICIO), None)
        if reemplazo is not None:
            lineas.append(f"Desalojo: {evento.proceso} fue desalojado por {reemplazo}")
    return lineas

def filas_memoria(motor: Motor) -> list[tuple[str, ...]]:
    tamanos = {pcb.id: pcb.tamano for pcb in motor.colas.todos()}
    filas = []
    for p in sorted(motor.memoria.particiones, key=lambda p: p.inicio):
        if p.estado == EstadoParticion.LIBRE:
            sobrante = p.tamano
        elif p.id == ID_SO
            sobrante = 0
        else:
            sobrante = p.tamano - tamanos[p.proceso]
        filas.append((
            str(p.id), f"{p.inicio}K", f"{p.tamano}K"
            p.estado.name, p.proceso or "-", f"{sobrante}K"
        ))
    return filas

def resumen_memoria(motor: Motor) -> tuple[int, int, int]:
    particiones = motor.memoria.particiones
    huecos = [p.tamano for p in particiones if p.estado == EstadoParticion.LIBRE]
    return sum(p.tamano for p in particiones), sum(huecos), max(huecos, default=0)

def formatear_memoria(motor: Motor) -> list[str]:
    total, libre, mayor_hueco = resumen_memoria(motor)
    return [
        "Memoria:",
        *_alinear([ENCABEZADO_MEMORIA, *filas_memoria(motor)], izquierda={3, 4}),
        f"  Total: {total}K"
        f"  Memoria libre: {libre}K"
        f"  Mayor hueco disponible: {mayor_hueco}K"
    ]

def formatear_colas(motor: Motor) -> list[str]:
    colas = motor.colas
    listos = sorted(colas.listo, key=clave_srtf)
    esperando = [p for p in colas.nuevo if p.arribo <= motor.reloj]
    por_arribar = [f"{p.id}(arribo {p.arribo})" for p in colas.nuevo if p.arribo > motor.reloj]
    terminados = [f"{p.id}(t={p.finalizacion})" for p in colas.terminado]
    en_cpu = 1 if colas.ejecucion is not None else 0
    return [
        "Colas:",
        f"  Listo: {_cola(listos)}",
        f"  Listo/Suspendido: {_cola(colas.listo_suspendido)}",
        f"  Nuevo: {_cola(esperando)}",
        f"  Por arribar: {_lista(por_arribar)}",
        f"  Terminados: {_lista(terminados)}",
        f"  Grado de multiprogramación: {motor.grado_multiprogramacion}/{GRADO_MAXIMO} "
        f"  (Ejecución {en_cpu} + Listo {len(colas.listo)} "
        f"+ Listo/Suspendido {len(colas.listo_suspendido)})"

    ]

def formatear_estado(motor: Motor) -> list[str]:
    return [
        *formatear_cpu(motor),
        *formatear_colas(motor),
        *formatear_memoria(motor)
    ]
    

def formatear_bloque(bloque: Bloque, motor: Motor) -> str:
    lineas = [f"========== t = {bloque.tiempo} =========="]
    for evento in bloque.eventos:
        lineas.append(f"{NOMBRES_EVENTO[evento.tipo]:<7} {evento.proceso}")
    lineas.append("-" * 26)
    lineas.extend(formatear_estado(motor))
    return "\n".join(lineas)

def ejecutar_pausas( motor: Motor, salida: Callable[[str], object] = print, esperar: Callable[[str], object] = input) -> list[Bloque]:
    bloques: list[Bloque] = []
    vistos = 0
    motor.procesar_instante()
    while True:
        nuevos = motor.eventos[vistos:]
        vistos = len(motor.eventos)
        visibles = tuple(e for e in nuevos if e.tipo in EVENTOS_VISIBLES)
        if visibles:
            bloque = Bloque(motor.reloj, visibles)
            bloques.append(bloque)
            salida(formatear_bloque(bloque, motor))
            try:
                esperar(PROMPT_FINAL if motor.terminado else PROMPT)
            except EOFError:
                salida("Entrada cerrada, simulación interrumpida")
                return bloques
        if motor.terminado:    
            return bloques
        motor.avanzar_reloj()
        motor.procesar_instante()
