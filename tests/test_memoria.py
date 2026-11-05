import pytest

from simulador.lectura import leer_procesos
from simulador.memoria import (
  ErrorMemoria, EstadoParticion, ID_SO, MEMORIA_TOTAL, Memoria, Particion,
)

def test_memoria_inicial_so_y_un_hueco_de_450():
  memoria = Memoria()
  assert len(memoria.particiones) == 2
  so, hueco = memoria.particiones
  assert (so.id, so.inicio, so.tamano, so.estado, so.proceso) == (
    ID_SO, 0, 100, EstadoParticion.OCUPADA, "SO"
  )
  assert (hueco.inicio, hueco.tamano, hueco.estado, hueco.proceso) == (
    100, 450, EstadoParticion.LIBRE, None
  )

def test_particion_registra_todos_los_campos():
  p = Particion(7, 120, 30, EstadoParticion.OCUPADA, "P1")
  assert (p.id, p.inicio, p.tamano, p.estado, p.proceso) == (
    7, 120, 30, EstadoParticion.OCUPADA, "P1"
  )

def test_ocupar_crea_particion_con_tamano_del_proceso_y_hueco_remanente():
  memoria = Memoria()
  p1 = memoria.ocupar(1, 120, "P1")
  assert (p1.inicio, p1.tamano, p1.estado, p1.proceso) == (
    100, 120, EstadoParticion.OCUPADA, "P1"
  )
  assert len(memoria.particiones) == 3
  remanente = memoria.particiones[2]
  assert (remanente.inicio, remanente.tamano, remanente.estado) == (
    220, 330, EstadoParticion.LIBRE
  )

def test_ocupar_tamano_exacto_no_deja_remanente():
  memoria = Memoria()
  memoria.ocupar(1, 450, "P1")
  assert len(memoria.particiones) == 2
  assert memoria.huecos() == []

def test_invariante_tras_varias_ocupaciones():
  memoria = Memoria()
  for proceso in leer_procesos("pruebas/10_procesos.txt"):
    huecos = [h for h in memoria.huecos() if h.tamano >= proceso.tamano]
    if not huecos:
      continue
    memoria.ocupar(huecos[0].id, proceso.tamano, proceso.id)
    assert sum(p.tamano for p in memoria.particiones) == MEMORIA_TOTAL
    memoria.verificar_invariante()

def test_ocupar_rechaza_operaciones_invalidas():
  memoria = Memoria()
  with pytest.raises(ErrorMemoria):
    memoria.ocupar(99, 10, "P1")
  with pytest.raises(ErrorMemoria):
    memoria.ocupar(ID_SO, 10, "P1")
  with pytest.raises(ErrorMemoria):
    memoria.ocupar(1, 451, "P1")
  with pytest.raises(ErrorMemoria):
    memoria.ocupar(1, 0, "P1")
  memoria.ocupar(1, 100, "P1")
  with pytest.raises(ErrorMemoria):
    memoria.ocupar(1, 10, "P2")

def test_invariante_detecta_solapamiento_y_hueco_perdido():
  memoria = Memoria()
  memoria.ocupar(1, 100, "P1")
  memoria.particiones[1].inicio -= 10
  with pytest.raises(ErrorMemoria, match="solapa"):
    memoria.verificar_invariante()

  memoria = Memoria()
  memoria.ocupar(1, 100, "P1")
  memoria.particiones[2].inicio += 10
  with pytest.raises(ErrorMemoria, match="perdido"):
    memoria.verificar_invariante()
