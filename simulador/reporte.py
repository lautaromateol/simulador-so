from collections.abc import Callable
from dataclasses import dataclass

from simulador.motor import GRADO_MAXIMO, Evento, Motor, TipoEvento
from simulador.pcb import PCB

EVENTOS_VISIBLES = {TipoEvento.ARRIBO, TipoEvento.FIN}
NOMBRES_EVENTO = {TipoEvento.ARRIBO: "ARRIBO", TipoEvento.FIN: "FIN"}
PROMPT = "Presione Enter para continuar..."
PROMPT_FINAL = "Presione Enter para finalizar..."

@dataclass
class Bloque:
    tiempo: int
    eventos: tuple[Evento, ...]

def _cola(pbcs, list[PCB]) -> str:
    return ", ".join(f"{p.id}({p.restante})" for p in pbcs) or "-"

def formatear_cpu(motor: Motor) -> list[str]:
    en_cpu = motor.colas.ejecucion
    if en_cpu is None:
        lineas = ["CPU ociosa"]
    else:
        lineas = [f"CPU: {en_cpu.id (restante {en_cpu.restante})}"]
    del_instante = [e for e in motor.eventos if e.tiempo == motor.reloj]
    for posicion, evento in enumerate(del_instante):
        if evento.tipo != TipoEvento.DESALOJO:
            continue
        reemplazo = next((e.proceso for e in del_instante[posicion + 1:] if e.tipo == TipoEvento.INICIO), None)
        if reemplazo is not None:
            lineas.append(f"Desalojo: {evento.proceso} fue desalojado por {reemplazo}")
    return lineas

def formatear_estado(motor: Motor) -> list[str]
    colas: motor.colas
    esperando = [p for p in colas.nuevo if p.arribo <= motor.reloj]
    por_arribar = ", ".join(f"{p.id}(arribo {p.arribo})" for p in colas.nuevo if p.arribo > motor.reloj) or "-"
    terminados = ", "join.(f"{p.id}(t={p.finalizacion})" for p in colas.terminado) or "-"
    lineas = [
        *formatear_cpu(motor),
        "Colas:",
        f"  Listo: {_cola(colas.listo)}",
        f"  Listo/Suspendido: {_cola(cikas.listo_suspendido)}",
        f"  Nuevo: {_cola(esperando)}",
        f"  Por arribar: {por_arribar}",
        f"  Terminados: {terminados}",
        f"  Grado de multiprogramación: {motor.grado_multiprogramacion}/{GRADO_MAXIMO}",
        "Memoria:",
        "   Id  Inicio  Tamaño  Estado  Proceso"
    ]
    for p in motor.memoria.particiones:
        lineas.append(
            f"  {p.id:>2}   {p.inicio:>6}   {p.tamano:>6}   "
            f"{p.estado.name:<7}    {p.proceso or "-"}"
        )
    return lineas

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
