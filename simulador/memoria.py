from dataclasses import dataclass
from enum import Enum, auto

from simulador.lectura import MEMORIA_USUARIO

TAMANO_SO = 100
MEMORIA_TOTAL = TAMANO_SO + MEMORIA_USUARIO
ID_SO = 0

class EstadoParticion(Enum):
  LIBRE = auto()
  OCUPADA = auto()

@dataclass
class Particion:
  id: int
  inicio: int
  tamano: int
  estado: EstadoParticion
  proceso: str | None = None

class ErrorMemoria(Exception):
  """Operación inválida sobre la memoria o invariante roto."""

class Memoria:
  def __init__(self) -> None:
    self.particiones: list[Particion] = [
      Particion(ID_SO, 0, TAMANO_SO, EstadoParticion.OCUPADA, "SO"),
      Particion(1, TAMANO_SO, MEMORIA_USUARIO, EstadoParticion.LIBRE)
    ]
    self._siguiente_id = 2
    self.verificar_invariante()

  def huecos(self) -> list[Particion]:
    return [p for p in self.particiones if p.estado == EstadoParticion.LIBRE]

  def mejor_hueco(self, tamano: int) -> Particion | None:
    if tamano <= 0:
      raise ErrorMemoria(f"El tamaño debe ser mayor que 0 (recibido: {tamano})")
    candidatos = [h for h in self.huecos() if h.tamano >= tamano]
    if not candidatos:
      return None
    return min(candidatos, key=lambda h: (h.tamano, h.inicio))

  def asig_bestfit(self, tamano: int, id_proceso: str) -> Particion | None:
    hueco = self.mejor_hueco(tamano)
    if hueco is None:
      return None
    return self.ocupar(hueco.id, tamano, id_proceso)

  def ocupar(self, id_hueco: int, tamano: int, id_proceso: str) -> Particion:
    if tamano <= 0:
      raise ErrorMemoria(f"El tamaño debe ser mayor que 0 (recibido: {tamano})")
    for indice, hueco in enumerate(self.particiones):
      if hueco.id == id_hueco:
        break
    else:
      raise ErrorMemoria(f"No existe la partición {id_hueco}")
    if hueco.estado != EstadoParticion.LIBRE:
      raise ErrorMemoria(f"La partición {id_hueco} no está libre")
    if tamano > hueco.tamano:
      raise ErrorMemoria(
        f"El proceso ({tamano}K) no entra en la partición {id_hueco} ({hueco.tamano}K)"
      )
    if tamano < hueco.tamano:
      remanente = Particion(
        self._siguiente_id,
        hueco.inicio + tamano,
        hueco.tamano - tamano,
        EstadoParticion.LIBRE
      )
      self._siguiente_id += 1
      self.particiones.insert(indice + 1, remanente)
      hueco.tamano = tamano

    hueco.estado = EstadoParticion.OCUPADA
    hueco.proceso = id_proceso
    self.verificar_invariante()
    return hueco

  def liberar(self, id_particion: int) -> Particion:
    if id_particion == ID_SO:
      raise ErrorMemoria("La partición del SO no se puede liberar")
    for indice, particion in enumerate(self.particiones):
      if particion.id == id_particion:
        break
    else:
      raise ErrorMemoria(f"No existe la partición {id_particion}")
    if particion.estado != EstadoParticion.OCUPADA:
      raise ErrorMemoria(f"La partición {id_particion} ya está libre")
      
    particion.estado = EstadoParticion.LIBRE
    particion.proceso = None

    if indice + 1 < len(self.particiones):
      siguiente = self.particiones[indice + 1]
      if siguiente.estado == EstadoParticion.LIBRE:
        particion.tamano += siguiente.tamano
        del self.particiones[indice + 1]

    anterior = self.particiones[indice - 1]
    if anterior.id != ID_SO and anterior.estado == EstadoParticion.LIBRE:
      anterior.tamano += particion.tamano
      del self.particiones[indice]
      particion = anterior

    self.verificar_invariante()
    return particion

  def verificar_invariante(self) -> None:
    if not self.particiones or self.particiones[0].id != ID_SO:
      raise ErrorMemoria("La primera partición debe ser la del SO")
    esperado = 0
    ids = set()
    for p in self.particiones:
      if p.id in ids:
        raise ErrorMemoria(f"Id de partición repetido: {p.id}")
      ids.add(p.id)
      if p.tamano <= 0:
        raise ErrorMemoria(f"La partición {p.id} tiene tamaño invalido: {p.tamano}")
      if p.inicio < esperado:
        raise ErrorMemoria(
          f"La partición {p.id} se solapa con la anterior "
          f"(inicia en {p.inicio}, se esperaba {esperado})"
        )
      if p.inicio > esperado:
        raise ErrorMemoria(
          f"Hueco perdido antes de la partición {p.id} "
          f"(inicia en {p.inicio}, se esperaba {esperado})"
        )
      if p.estado == EstadoParticion.LIBRE and p.proceso is not None:
        raise ErrorMemoria(f"La partición libre {p.id} tiene proceso asignado")
      if p.estado == EstadoParticion.OCUPADA and p.proceso is None:
        raise ErrorMemoria(f"La partición ocupada {p.id} no tiene proceso asignado")
      esperado += p.tamano
    if esperado != MEMORIA_TOTAL:
      raise ErrorMemoria(
        f"La suma de particiones es {esperado}K y debe ser {MEMORIA_TOTAL}K"
      )