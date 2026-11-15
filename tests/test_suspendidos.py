"""HU-11: Gestión de Listo/Suspendido por falta de memoria."""

from simulador.lectura import Proceso
from simulador.motor import GRADO_MAXIMO, Motor, TipoEvento
from simulador.pcb import PCB, Estado
from simulador.planificador import crear_motor_srtf


def proceso(id_proceso: str, tamano: int, irrupcion: int, arribo: int = 0) -> Proceso:
  return Proceso(id_proceso, tamano, arribo, irrupcion)


def pcb(motor: Motor, id_proceso: str) -> PCB:
  return next(p for p in motor.colas.todos() if p.id == id_proceso)


def mapa_memoria(motor: Motor) -> list[tuple[int, int, str | None]]:
  return [(p.inicio, p.tamano, p.proceso) for p in motor.memoria.particiones]


def test_proceso_admitido_sin_memoria_pasa_a_listo_suspendido():
  """Criterio 1: sin hueco Best-Fit suficiente pasa a Listo/Suspendido y cuenta para el grado."""
  motor = crear_motor_srtf([proceso("P1", 400, 5), proceso("P2", 100, 3)])
  motor.procesar_instante()

  p1, p2 = pcb(motor, "P1"), pcb(motor, "P2")
  assert motor.colas.ejecucion is p1
  assert p2.estado == Estado.LISTO_SUSPENDIDO
  assert p2.particion is None
  assert motor.colas.listo_suspendido == [p2]
  assert motor.grado_multiprogramacion == 2
  assert any(e.tipo == TipoEvento.SUSPENSION and e.proceso == "P2" for e in motor.eventos)


def test_listo_suspendido_cuenta_para_el_limite_de_5():
  """Criterio 1: los suspendidos ocupan cupo; el sexto queda en Nuevo aunque haya memoria."""
  motor = crear_motor_srtf([
    proceso("P1", 400, 10),
    *(proceso(f"P{i}", 100, 2) for i in range(2, 6)),
    proceso("P6", 10, 1),
  ])
  motor.procesar_instante()

  assert len(motor.colas.listo_suspendido) == 4
  assert motor.grado_multiprogramacion == GRADO_MAXIMO
  # P6 entraría en el hueco de 50K, pero no hay cupo.
  assert motor.memoria.mejor_hueco(10) is not None
  assert pcb(motor, "P6").estado == Estado.NUEVO


def test_proceso_en_listo_suspendido_no_puede_ser_elegido_por_planificador():
  """Criterio 3: un suspendido nunca ejecuta, aunque tenga menor tiempo restante."""
  motor = crear_motor_srtf([proceso("P1", 400, 5), proceso("P2", 100, 3)])
  motor.procesar_instante()

  p1, p2 = pcb(motor, "P1"), pcb(motor, "P2")
  assert p2.restante < p1.restante
  assert motor.colas.ejecucion is p1
  assert p2.estado == Estado.LISTO_SUSPENDIDO

  motor.ejecutar()
  destinos = [(t.origen, t.destino) for t in p2.historial]
  assert destinos == [
    (Estado.NUEVO, Estado.LISTO_SUSPENDIDO),
    (Estado.LISTO_SUSPENDIDO, Estado.LISTO),
    (Estado.LISTO, Estado.EJECUCION),
    (Estado.EJECUCION, Estado.TERMINADO),
  ]
  assert p2.historial[2].tiempo == 5  # solo ejecuta cuando P1 terminó


def test_reactivacion_al_liberar_memoria_con_best_fit():
  """Criterios 2 y 4: al liberarse memoria pasa a Listo con Best-Fit y se actualiza la tabla."""
  motor = crear_motor_srtf([proceso("P1", 350, 2), proceso("P2", 200, 4)])
  motor.procesar_instante()
  assert pcb(motor, "P2").estado == Estado.LISTO_SUSPENDIDO

  motor.avanzar_reloj()
  assert motor.reloj == 2
  motor.procesar_instante()

  p2 = pcb(motor, "P2")
  assert pcb(motor, "P1").estado == Estado.TERMINADO
  assert motor.colas.listo_suspendido == []
  assert motor.colas.ejecucion is p2
  assert mapa_memoria(motor) == [(0, 100, "SO"), (100, 200, "P2"), (300, 250, None)]
  particion = next(p for p in motor.memoria.particiones if p.proceso == "P2")
  assert p2.particion == particion.id
  assert any(
    e.tipo == TipoEvento.REASIGNACION and e.proceso == "P2" and e.tiempo == 2
    for e in motor.eventos
  )
  motor.memoria.verificar_invariante()


def test_reactivacion_fifo_no_bloqueante_supuesto_9():
  """Supuesto 9: FIFO por orden de suspensión; uno que no entra no bloquea a los siguientes."""
  motor = crear_motor_srtf([
    proceso("P1", 350, 5),
    proceso("P2", 100, 2),
    proceso("P3", 200, 4),
    proceso("P4", 50, 3),
  ])
  motor.procesar_instante()

  p3, p4 = pcb(motor, "P3"), pcb(motor, "P4")
  assert motor.memoria.huecos() == []
  assert motor.colas.listo_suspendido == [p3, p4]
  assert motor.colas.ejecucion is pcb(motor, "P2")

  motor.avanzar_reloj()  # t=2: termina P2 y libera 100K
  motor.procesar_instante()

  assert p3.estado == Estado.LISTO_SUSPENDIDO
  assert motor.colas.listo_suspendido == [p3]
  assert motor.colas.ejecucion is p4  # reactivado y elegido por SRTF (3 < 5)
  assert mapa_memoria(motor) == [
    (0, 100, "SO"), (100, 350, "P1"), (450, 50, "P4"), (500, 50, None),
  ]
  motor.memoria.verificar_invariante()


def test_prueba_tecnica_proceso_grande_espera_hasta_fusion_de_huecos():
  """Criterio 5: un proceso grande espera hasta que la fusión de huecos le deja lugar."""
  motor = crear_motor_srtf([
    proceso("P1", 150, 3),
    proceso("P2", 150, 4),
    proceso("P3", 150, 10),
    proceso("PG", 250, 6),
  ])
  motor.procesar_instante()

  pg = pcb(motor, "PG")
  assert motor.memoria.huecos() == []
  assert pg.estado == Estado.LISTO_SUSPENDIDO
  assert motor.grado_multiprogramacion == 4

  motor.avanzar_reloj()  # t=3: termina P1, queda un hueco de 150K
  motor.procesar_instante()
  assert motor.reloj == 3
  assert [h.tamano for h in motor.memoria.huecos()] == [150]
  assert pg.estado == Estado.LISTO_SUSPENDIDO
  assert motor.colas.ejecucion is pcb(motor, "P2")

  motor.avanzar_reloj()  # t=7: termina P2, su hueco se fusiona con el de P1 (300K)
  motor.procesar_instante()
  assert motor.reloj == 7
  assert pg.estado == Estado.EJECUCION
  assert motor.colas.listo_suspendido == []
  assert mapa_memoria(motor) == [
    (0, 100, "SO"), (100, 250, "PG"), (350, 50, None), (400, 150, "P3"),
  ]
  motor.memoria.verificar_invariante()

  motor.ejecutar()
  assert motor.terminado
  assert motor.errores_internos == []
