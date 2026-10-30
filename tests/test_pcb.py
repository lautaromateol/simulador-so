from simulador.lectura import leer_procesos
from simulador.pcb import PCB, Colas, Estado, inicializar

def test_pcb_nace_nuevo_con_restante_igual_a_irrupcion():
  procesos = leer_procesos("pruebas/10_procesos.txt")
  colas = inicializar(procesos)
  assert len(colas.nuevo) == len(procesos)
  for pcb in colas.nuevo:
    assert pcb.estado == Estado.NUEVO
    assert pcb.restante == pcb.irrupcion
    assert pcb.particion is None
    assert pcb.finalizacion is None

def test_demas_colas_empiezan_vacias():
  colas = inicializar(leer_procesos("pruebas/10_procesos.txt"))
  assert colas.listo == []
  assert colas.listo_suspendido == []
  assert colas.ejecucion is None
  assert colas.terminado == []

def test_colas_no_comparten_listas():
  a, b = Colas(), Colas()
  a.listo.append(object())
  assert b.listo == []
