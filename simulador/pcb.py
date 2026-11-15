from dataclasses import dataclass, field
from enum import Enum, auto

from simulador.lectura import Proceso

class Estado(Enum):
  NUEVO = auto()
  LISTO = auto()
  LISTO_SUSPENDIDO = auto()
  EJECUCION = auto()
  TERMINADO = auto()

class ErrorTransicion(Exception):
  """Transición de estado inválida: error interno del simulador."""

TRANSICIONES_VALIDAS: frozenset[tuple[Estado, Estado]] = frozenset({
  (Estado.NUEVO, Estado.LISTO),
  (Estado.NUEVO, Estado.LISTO_SUSPENDIDO),
  (Estado.LISTO_SUSPENDIDO, Estado.LISTO),
  (Estado.LISTO, Estado.EJECUCION),
  (Estado.EJECUCION, Estado.LISTO),
  (Estado.EJECUCION, Estado.TERMINADO),
})

@dataclass(frozen=True)
class Transicion:
  tiempo: int
  proceso: str
  origen: Estado
  destino: Estado

  def __str__(self) -> str:
    return (
      f"t={self.tiempo} {self.proceso}: "
      f"{self.origen.name} -> {self.destino.name}"
    )

@dataclass
class PCB:
  id: str
  tamano: int
  arribo: int
  irrupcion: int
  restante: int
  estado: Estado = Estado.NUEVO
  particion: int | None = None
  finalizacion: int | None = None
  historial: list[Transicion] = field(
    default_factory=list, compare=False, repr=False
  )
  errores_internos: list[str] = field(
    default_factory=list, compare=False, repr=False
  )

  @classmethod
  def desde_proceso(cls, proceso: Proceso) -> "PCB":
    return cls(
      id=proceso.id,
      tamano=proceso.tamano,
      arribo=proceso.arribo,
      irrupcion=proceso.irrupcion,
      restante=proceso.irrupcion,
      estado=Estado.NUEVO
    )

def transicionar(self, destino: Estado, tiempo: int) -> Transicion:
  origen = self.estado
  if (origen, destino) not in TRANSICIONES_VALIDAS:
    mensaje = (
      f"Transición inválida de '{self.id}' en t={tiempo}:"
      f"{origen.name} -> {destino.name}"
    )
    self.errores_internos.append(mensaje)
    raise ErrorTransicion(mensaje)
  self.estado = destino
  transicion = Transicion(tiempo, self.id, origen, destino)
  self.historial.append(transicion)
  return transicion

@dataclass
class Colas:
  nuevo: list[PCB] = field(default_factory=list)
  listo: list[PCB] = field(default_factory=list)
  listo_suspendido: list[PCB] = field(default_factory=list)
  ejecucion: PCB | None = None
  terminado: list[PCB] = field(default_factory=list)

def todos(self) -> list[PCB]:
  pcbs = [*self.nuevo, *self.listo, *self.listo_suspendido, *self.terminado]
  if self.ejecucion is not None:
    pcbs.append(self.ejecucion)
  return pcbs

def inicializar(procesos: list[Proceso]) -> Colas:
  colas = Colas()
  colas.nuevo = [PCB.desde_proceso(p) for p in procesos]
  return colas