import re 
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from simulador.lectura import Proceso
from simulador.memoria import Memoria
from simulador.pcb import PCB, Colas, Estado, Transicion, inicializar

GRADO_MAXIMO = 5

class ErrorMotor(Exception):
    """Error o estado inconsistente en el motor de simulación."""

class TipoEvento(Enum):
    ARRIBO = auto()
    ADMISION = auto()
    SUSPENSION = auto()
    REASIGNACION = auto()
    INICIO = auto()
    DESALOJO = auto()
    FIN = auto()

@dataclass(frozen=True)
class Evento:
    tiempo: int
    tipo: TipoEvento
    proceso: str
    grado: int

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
        self.memoria: Memoria = Memoria()
        self.colas.nuevo.sort(key=lambda pcb: (pcb.arribo, clave_id(pcb.id)))
        self.reloj: int = self.colas.nuevo[0].arribo
        self.ociosos: list[tuple[int, int]] = []
        self.eventos: list[Evento] = []
        self._arribos_registrados: set[str] = set()
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
    def grado_multiprogramacion(self) -> int:
        c = self.colas
        return (len(c.listo) + len(c.listo_suspendido) + (1 if c.ejecucion is not None else 0))

    @property
    def log_transiciones(self) -> dict[str, list[Transicion]]:
        pcbs = sorted(self.colas.todos(), key=lambda pcb: clave_id(pcb.id))
        return {pcb.id: list(pcb.historial) for pcb in pcbs}

    @property
    def errores_internos(self) -> list[str]:
        return [e for pcb in self.colas.todos() for e in pcb.errores_internos]

    def verificar_multiprogramacion(self) -> None:
        grado = self.grado_multiprogramacion
        if grado > GRADO_MAXIMO:
            raise ErrorMotor(
                f"Grado de multiprogramación excedido en t={self.reloj}: "
                f"{grado} > {GRADO_MAXIMO}"
            )

    def procesar_instante(self) -> None:
        self._finalizar()
        self._reintentar_suspendidos()
        self._registrar_arribos()
        self._admitir()
        self._seleccionar()

    def _finalizar(self) -> None:
        colas = self.colas
        en_ejecucion = colas.ejecucion
        if en_ejecucion is not None and en_ejecucion.restante == 0:
            en_ejecucion.transicionar(Estado.TERMINADO, self.reloj)
            en_ejecucion.finalizacion = self.reloj
            self._liberar_memoria(en_ejecucion)
            colas.terminado.append(en_ejecucion)
            colas.ejecucion = None
            self._registrar(TipoEvento.FIN, en_ejecucion)

    def _seleccionar(self) -> None:
        colas = self.colas

        if (self._desaloja is not None and colas.ejecucion is not None and colas.listo):
            candidato = self._elegir(colas.listo)
            if self._desaloja(colas.ejecucion, candidato):
                desalojado = colas.ejecucion
                desalojado.transicionar(Estado.LISTO, self.reloj)
                colas.listo.append(desalojado)
                colas.ejecucion = None
                self._registrar(TipoEvento.DESALOJO, desalojado)

        if colas.ejecucion is None and colas.listo:
            pcb = self._elegir(colas.listo)
            try:
                colas.listo.remove(pcb)
            except ValueError:
                raise ErrorMotor("La política eligió un proceso que no está en listos") from None
            if pcb.particion is None:
                raise ErrorMotor(f"'{pcb.id}' no tiene partición asignada")
            pcb.transicionar(Estado.EJECUCION, self.reloj)
            colas.ejecucion = pcb
            self._registrar(TipoEvento.INICIO, pcb)

    def avanzar_reloj(self) -> None:
        colas = self.colas
        if colas.ejecucion is None and colas.listo:
            raise ErrorMotor("Hay procesos listos y la CPU libre: falta llamar a procesar_instante()")
        if self._hay_admisibles():
            raise ErrorMotor("Hay procesos para admitir: falta llamar a procesar_instante()")

        candidatos = []
        proximo_arribo = next((p.arribo for p in colas.nuevo if p.arribo > self.reloj), None)
        if proximo_arribo is not None:
            candidatos.append(proximo_arribo)
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
        while not self.terminado:
            self.avanzar_reloj()
            self.procesar_instante()

    def _hay_admisibles(self) -> bool:
        nuevo = self.colas.nuevo
        return (
            bool(nuevo) and nuevo[0].arribo <= self.reloj
            and self.grado_multiprogramacion < GRADO_MAXIMO
        )

    def _admitir(self) -> None:
        colas = self.colas
        while self._hay_admisibles():
            pcb = colas.nuevo[0]
            hueco = self.memoria.mejor_hueco(pcb.tamano)
            if hueco is not None:
                pcb.transicionar(Estado.LISTO, self.reloj)
                pcb.particion = self.memoria.ocupar(hueco.id, pcb.tamano, pcb.id).id
                colas.nuevo.pop(0)
                colas.listo.append(pcb)
                self._registrar(TipoEvento.ADMISION, pcb)
            else:
                pcb.transicionar(Estado.LISTO_SUSPENDIDO, self.reloj)
                colas.nuevo.pop(0)
                colas.listo_suspendido.append(pcb)
                self._registrar(TipoEvento.SUSPENSION, pcb)

    def _reintentar_suspendidos(self) -> None:
        colas = self.colas
        for pcb in list(colas.listo_suspendido):
            hueco = self.memoria.mejor_hueco(pcb.tamano)
            if hueco is None:
                continue
            pcb.transicionar(Estado.LISTO, self.reloj)
            pcb.particion = self.memoria.ocupar(hueco.id, pcb.tamano, pcb.id).id
            colas.listo_suspendido.remove(pcb)
            colas.listo.append(pcb)
            self._registrar(TipoEvento.REASIGNACION, pcb)
    
    def _liberar_memoria(self, pcb: PCB) -> None:
        if pcb.particion is None:
            raise ErrorMotor(f"'{pcb.id}' no tiene partición para liberar")
        self.memoria.liberar(pcb.particion)
        pcb.particion = None

    def _registrar_arribos(self) -> None:
        for pcb in self.colas.nuevo:
            if pcb.arribo > self.reloj:
                break
            if pcb.id not in self._arribos_registrados:
                self._arribos_registrados.add(pcb.id)
                self._registrar(TipoEvento.ARRIBO, pcb)

    def _registrar(self, tipo: TipoEvento, pcb: PCB) -> None:
        self.verificar_multiprogramacion()
        self.eventos.append(Evento(self.reloj, tipo, pcb.id, self.grado_multiprogramacion))

