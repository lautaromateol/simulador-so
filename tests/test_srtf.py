"""HU-07 (reloj), HU-08 (SRTF), HU-10 (límite de 5) y HU-12 (orden determinista)."""

from simulador.lectura import Proceso, leer_procesos
from simulador.motor import GRADO_MAXIMO, Motor, TipoEvento
from simulador.pcb import PCB, Estado
from simulador.planificador import crear_motor_srtf, desaloja_srtf, elegir_srtf


def proceso(id_proceso: str, irrupcion: int, arribo: int, tamano: int = 10) -> Proceso:
  return Proceso(id_proceso, tamano, arribo, irrupcion)


def simular(procesos: list[Proceso]) -> Motor:
  motor = crear_motor_srtf(procesos)
  motor.ejecutar()
  return motor


def finalizaciones(motor: Motor) -> dict[str, int]:
  return {p.id: p.finalizacion for p in motor.colas.terminado}


def eventos(motor: Motor, tipo: TipoEvento) -> list[tuple[int, str]]:
  return [(e.tiempo, e.proceso) for e in motor.eventos if e.tipo == tipo]


# Caso clásico de libro (Silberschatz): P1 0-1, P2 1-5, P4 5-10, P1 10-17, P3 17-26.
CASO_LIBRO = [proceso("P1", 8, 0), proceso("P2", 4, 1), proceso("P3", 9, 2), proceso("P4", 5, 3)]


# ---------- HU-08: SRTF apropiativo ----------

def test_prueba_tecnica_caso_clasico_de_libro():
  motor = simular(CASO_LIBRO)

  assert finalizaciones(motor) == {"P1": 17, "P2": 5, "P3": 26, "P4": 10}
  assert eventos(motor, TipoEvento.INICIO) == [
    (0, "P1"), (1, "P2"), (5, "P4"), (10, "P1"), (17, "P3"),
  ]
  esperas = [p.finalizacion - p.arribo - p.irrupcion for p in motor.colas.terminado]
  assert sum(esperas) / len(esperas) == 6.5


def test_desalojo_devuelve_a_listo_conservando_tiempo_restante():
  motor = crear_motor_srtf(CASO_LIBRO)
  motor.procesar_instante()
  motor.avanzar_reloj()  # t=1, arriba P2
  motor.procesar_instante()

  p1 = next(p for p in motor.colas.listo if p.id == "P1")
  assert motor.colas.ejecucion.id == "P2"
  assert p1.estado == Estado.LISTO
  assert p1.restante == 7
  assert eventos(motor, TipoEvento.DESALOJO) == [(1, "P1")]


def test_tiempo_restante_igual_no_desaloja():
  """Supuesto 6: solo desaloja si el restante del que llega es estrictamente menor."""
  motor = simular([proceso("P1", 5, 0), proceso("P2", 4, 1)])

  assert eventos(motor, TipoEvento.DESALOJO) == []
  assert finalizaciones(motor) == {"P1": 5, "P2": 9}
  assert desaloja_srtf(PCB("A", 10, 0, 5, restante=4), PCB("B", 10, 1, 4, restante=4)) is False
  assert desaloja_srtf(PCB("A", 10, 0, 5, restante=4), PCB("B", 10, 1, 3, restante=3)) is True


def test_desempate_por_menor_arribo_y_luego_menor_id():
  por_arribo = [PCB("P1", 10, arribo=3, irrupcion=4, restante=4),
                PCB("P2", 10, arribo=1, irrupcion=4, restante=4)]
  assert elegir_srtf(por_arribo).id == "P2"

  # Mismo restante y arribo: Id con orden natural (P2 antes que P10).
  por_id = [PCB("P10", 10, arribo=0, irrupcion=4, restante=4),
            PCB("P2", 10, arribo=0, irrupcion=4, restante=4)]
  assert elegir_srtf(por_id).id == "P2"


def test_al_terminar_elige_el_de_menor_restante():
  motor = simular([proceso("P1", 3, 0), proceso("P2", 6, 1), proceso("P3", 2, 1),
                   proceso("P4", 4, 2)])

  assert eventos(motor, TipoEvento.INICIO) == [(0, "P1"), (3, "P3"), (5, "P4"), (9, "P2")]


def test_un_solo_proceso_en_ejecucion_en_cada_instante():
  motor = crear_motor_srtf(leer_procesos("pruebas/10_procesos.txt"))
  motor.procesar_instante()
  while True:
    assert sum(p.estado == Estado.EJECUCION for p in motor.colas.todos()) <= 1
    if motor.terminado:
      break
    motor.avanzar_reloj()
    motor.procesar_instante()


def test_la_memoria_puede_postergar_al_de_menor_restante():
  """Mismo caso de libro con tamaños reales: P4 (90K) queda en Listo/Suspendido."""
  motor = simular(leer_procesos("procesos.txt"))

  assert eventos(motor, TipoEvento.SUSPENSION) == [(3, "P4")]
  assert eventos(motor, TipoEvento.REASIGNACION) == [(12, "P4")]
  assert finalizaciones(motor) == {"P1": 12, "P2": 5, "P3": 26, "P4": 17}


# ---------- HU-07: reloj y eventos ----------

def test_reloj_inicia_en_el_menor_arribo():
  motor = crear_motor_srtf([proceso("P1", 2, 7), proceso("P2", 2, 3)])
  assert motor.reloj == 3


def test_reloj_avanza_al_proximo_evento_y_descuenta_restante():
  motor = crear_motor_srtf([proceso("P1", 10, 0), proceso("P2", 20, 4)])
  motor.procesar_instante()

  motor.avanzar_reloj()
  assert motor.reloj == 4  # próximo arribo antes que el fin de P1
  assert motor.colas.ejecucion.restante == 6

  motor.procesar_instante()
  motor.avanzar_reloj()
  assert motor.reloj == 10  # fin de P1


def test_cpu_ociosa_salta_al_proximo_arribo_y_registra_tiempo_ocioso():
  motor = simular([proceso("P1", 2, 0), proceso("P2", 1, 5), proceso("P3", 1, 9)])

  assert motor.ociosos == [(2, 5), (6, 9)]
  assert motor.tiempo_ocioso == 6
  assert finalizaciones(motor) == {"P1": 2, "P2": 6, "P3": 10}


def test_arribos_simultaneos_se_procesan_en_orden_de_id():
  motor = simular([proceso("P10", 3, 0), proceso("P2", 3, 0), proceso("P1", 3, 0)])

  assert eventos(motor, TipoEvento.ARRIBO) == [(0, "P1"), (0, "P2"), (0, "P10")]
  assert eventos(motor, TipoEvento.ADMISION) == [(0, "P1"), (0, "P2"), (0, "P10")]


# ---------- HU-10: grado de multiprogramación ----------

def test_prueba_tecnica_grado_nunca_supera_5_con_10_procesos():
  motor = simular([proceso(f"P{i}", 3, i // 3) for i in range(1, 11)])

  grados = [e.grado for e in motor.eventos]
  assert max(grados) == GRADO_MAXIMO
  assert all(g <= GRADO_MAXIMO for g in grados)
  assert len(motor.colas.terminado) == 10


def test_con_cupo_lleno_queda_en_nuevo_hasta_que_termine_alguno():
  motor = crear_motor_srtf([proceso(f"P{i}", 2 + i, 0) for i in range(1, 7)])
  motor.procesar_instante()

  p6 = next(p for p in motor.colas.todos() if p.id == "P6")
  assert motor.grado_multiprogramacion == GRADO_MAXIMO
  assert p6.estado == Estado.NUEVO

  motor.avanzar_reloj()  # t=3, termina P1
  motor.procesar_instante()
  assert p6.estado == Estado.LISTO
  assert eventos(motor, TipoEvento.ADMISION)[-1] == (3, "P6")


# ---------- HU-12: orden determinista ----------

def test_eventos_simultaneos_fin_antes_que_admision_y_seleccion():
  """En t=4: termina P1, se reactiva P2 y luego se admite el arribo P3."""
  motor = simular([proceso("P1", 4, 0, tamano=400), proceso("P2", 2, 0, tamano=100),
                   proceso("P3", 1, 4, tamano=10)])

  en_t4 = [(e.tipo, e.proceso) for e in motor.eventos if e.tiempo == 4]
  assert en_t4 == [
    (TipoEvento.FIN, "P1"),
    (TipoEvento.REASIGNACION, "P2"),
    (TipoEvento.ARRIBO, "P3"),
    (TipoEvento.ADMISION, "P3"),
    (TipoEvento.INICIO, "P3"),
  ]


def test_prueba_tecnica_misma_entrada_misma_salida():
  procesos = leer_procesos("pruebas/10_procesos.txt")
  assert simular(procesos).eventos == simular(procesos).eventos
