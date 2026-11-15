from simulador.lectura import Proceso
from simulador.motor import Motor, clave_id
from simulador.pcb import PCB

def clave_srtf(pcb: PCB) -> tuple[int, int, list[tuple[int, int, str]]]:
    return (pcb.restante, pcb.arribo, clave_id(pcb.id))

def elegir_srtf(listos: list[PCB]) -> PCB:
    return min(listos, key=clave_srtf)

def desaloja_srtf(en_ejecucion: PCB, candidato: PCB) -> bool:
    return candidato.restante < en_ejecucion.restante

def crear_motor_srtf(procesos: list[Proceso]) -> Motor:
    return Motor(procesos, elegir=elegir_srtf, desaloja=desaloja_srtf)