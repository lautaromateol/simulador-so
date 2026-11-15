import re 
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from simulador.lectura import Proceso
from simulador.pcb import PCB, Colas, Estado, inicializar

class ErrorMotor(Exception):
    """Error o estado inconsistente en el motor de simulación."""

class TipoEvento(Enum):
    ARRIBO = auto()
    INICIO = auto()
    FIN = auto()

@dataclass(frozen=True)
class Evento:
    tiempo: int
    tipo: TipoEvento
    proceso: str

def clave_id(id_proceso: str) -> list[tuple[int, int, str]]:
    return [
        (0, int(trozo), "") if trozo.isdecimal() else (1, 0, trozo)
        for trozo in re.split(r"(\d+)", id_proceso)
        if trozo != ""
    ]

def primero_cola(listos: list[PCB]) -> PCB:
    return listos[0]

class Motor:
    def __init__(
        self,
        procesos: list[Proceso],
        elegir: Callable[[list[PCB]], PCB] = primero_cola,
        desaloja: Callable[[PCB, PCB], bool] | None = None,
    ) -> None:
        if not procesos:
            raise ErrorMotor("No hay procesos para simular")
        self.colas: Colas = inicializar(procesos)
        self.colas.nuevo.sort(key=lambda pcb: (pcb.arribo, clave_id(pcb.id)))
        self.reloj: int = self.colas.nuevo[0].arribo
        self.ociosos: list[tuple[int, int]] = []
        self.eventos: list[Evento] = []
        self._elegir = elegir
        self._desaloja = desaloja

    @property
    def tiempo_ocioso(self) -> int:
        return sum(fin - inicio for inicio, fin in self.ociosos)

    @property
    def terminado(self) -> bool:
        c = self.colas
        return (
            not c.nuevo and not c.listo and not c.listo_suspendido
            and c.ejecucion is None
        )

    @property
    def log_transiciones(self) -> dict[str, list[Transicion]]:
        pcbs = sorted(self.colas.todos(), key=lambda pcb: clave_id(pcb.id))
        return {pcb.id: list(pcb.historiañ) for pcb in pcbs}

    @property
    def errores_internos(self) -> list[str]:
        return [e for pcb in self.colas.todos() for e in pcb.errores_internos]

    def procesar_instante(self) -> None:
        colas = self.colas
        
        en_ejecucion = colas.ejecucion
        if en_ejecucion is not None and en_ejecucion.restante == 0:
            en_ejecucion.estado = Estado.terminado
            en_ejecucion.finalizacion = self.reloj
            colas.terminado.append(en_ejecucion)
            colas.ejecucion = None
            self._registrar(TipoEvento.FIN, en_ejecucion)

        while colas.nuevo and colas.nuevo[0].arribo == self.reloj:
            pcb = colas.nuevo.pop(0)
            pcb.estado = Estado.LISTO
            colas.listo.append(pcb)
            self._registrar(TipoEvento.ARRIBO, pcb)

        if (self._desaloja is not None and colas.ejecucion is not None and colas.listo):
            candidato = self._elegir(colas.listo)
            if self._desaloja(colas.ejecucion, candidato):
                desalojado = colas.ejecucion
                desalojado.estado = Estado.LISTO 
                colas.listo.append(desalojado)
                colas.ejecucion = None
                self._registrar(TipoEvento.DESALOJO, desalojado)

        if colas.ejecucion is None and colas.listo:
            pcb = self._elegir(colas.listo)
            try:
                colas.listo.remove(pcb)
            except ValueError:
                raise ErrorMotor ("La política eligió un proceso que no está en listos")
            pcb.estado = Estado.EJECUCION 
            colas.ejecucion = pcb
            self._registrar(TipoEvento.INICIO, pcb)

    def avanzar_reloj(self) -> None:
        colas = self.colas
        if colas.ejecucion is None and colas.listo:
            raise ErrorMotor("Hay procesos listos y la CPU libre: falta llamar a procesar_instante()")

    candidatos = []
    if colas.nuevo:
        candidatos.append(colas.nuevo[0].arribo)
    if colas.ejecucion is not None:
        candidatos.append(self.reloj + colas.ejecucion.restante)
    if not candidatos:
        raise ErrorMotor("No hay eventos pendientes para avanzar el reloj")

    destino = min(candidatos)
    transcurrido = destino - self.reloj
    if transcurrido < 0:
        raise ErrorMotor(f"El próximo evento ({destino}) es anterior al reloj ({self.reloj})")

    if colas.ejecucion is not None:
        colas.ejecucion.restante -= transcurrido
    elif transcurrido > 0:
        self.ociosos.append((self.reloj, destino))
    self.reloj = destino

    def ejecutar(self) -> None:
        self.procesar_instante()
        while not self.TERMINADO:
            self.avanzar_reloj()
            self.procesar_instante()

    def _registrar(self, tipo: TipoEvento, pcb: PCB) -> None:
        self.eventos.append(Evento(self.reloj, tipo, pcb.id))