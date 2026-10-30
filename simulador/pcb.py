from dataclasses import dataclass, field
from enum import Enum, auto

from simulador.lectura import Proceso

class Estado(Enum):
  NUEVO = auto()
  LISTO = auto()
  LISTO_SUSPENDIDO = auto()
  EJECUCION = auto()
  TERMINADO = auto()

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

@dataclass
class Colas:
  nuevo: list[PCB] = field(default_factory=list)
  listo: list[PCB] = field(default_factory=list)
  listo_suspendido: list[PCB] = field(default_factory=list)
  ejecucion: PCB | None = None
  terminado: list[PCB] = field(default_factory=list)

def inicializar(procesos: list[Proceso]) -> Colas:
  colas = Colas()
  colas.nuevo = [PCB.desde_proceso(p) for p in procesos]
  return colas