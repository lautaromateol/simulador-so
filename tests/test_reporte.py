"""HU-13 a HU-17: salida evento por evento e informe final."""

import re

import pytest

from simulador.lectura import Proceso, leer_procesos
from simulador.motor import GRADO_MAXIMO, Motor, TipoEvento
from simulador.planificador import crear_motor_srtf
from simulador.reporte import (
  PROMPT,
  PROMPT_FINAL,
  Bloque,
  ErrorReporte,
  calcular_metricas,
  ejecutar_pausas,
  filas_informe,
  filas_memoria,
  formatear_colas,
  formatear_informe,
  formatear_memoria,
  resumen_memoria,
)


def proceso(id_proceso: str, irrupcion: int, arribo: int, tamano: int = 10) -> Proceso:
  return Proceso(id_proceso, tamano, arribo, irrupcion)


# Caso clásico de libro (Silberschatz): P1 0-1, P2 1-5, P4 5-10, P1 10-17, P3 17-26.
CASO_LIBRO = [proceso("P1", 8, 0), proceso("P2", 4, 1), proceso("P3", 9, 2), proceso("P4", 5, 3)]
SIMULTANEOS = [proceso(f"P{i}", i, 0, tamano=100) for i in range(1, 8)]


class Corrida:
  """Ejecuta la simulación con pausas y guarda lo mostrado en cada bloque."""

  def __init__(self, procesos: list[Proceso]) -> None:
    self.motor: Motor = crear_motor_srtf(procesos)
    self.salidas: list[str] = []
    self.pausas: list[str] = []
    self.memorias: list[list[tuple[str, ...]]] = []
    self.bloques: list[Bloque] = ejecutar_pausas(
      self.motor, salida=self.salidas.append, esperar=self._esperar
    )

  def _esperar(self, prompt: str) -> None:
    self.pausas.append(prompt)
    self.memorias.append(filas_memoria(self.motor))

  def texto(self, tiempo: int) -> str:
    return next(s for b, s in zip(self.bloques, self.salidas) if b.tiempo == tiempo)

  def linea_cpu(self, tiempo: int) -> str:
    return self.texto(tiempo).splitlines()[len(self.bloque(tiempo).eventos) + 2]

  def bloque(self, tiempo: int) -> Bloque:
    return next(b for b in self.bloques if b.tiempo == tiempo)


def eventos(bloque: Bloque) -> list[tuple[TipoEvento, str]]:
  return [(e.tipo, e.proceso) for e in bloque.eventos]


def avanzar_hasta(motor: Motor, tiempo: int) -> None:
  motor.procesar_instante()
  while motor.reloj < tiempo:
    motor.avanzar_reloj()
    motor.procesar_instante()
  assert motor.reloj == tiempo


# ---------- HU-13: ejecución evento por evento con pausa ----------

def test_prueba_tecnica_n_arribos_y_n_finalizaciones():
  corrida = Corrida(leer_procesos("pruebas/10_procesos.txt"))

  todos = [e for b in corrida.bloques for e in b.eventos]
  arribos = sorted(e.proceso for e in todos if e.tipo == TipoEvento.ARRIBO)
  fines = sorted(e.proceso for e in todos if e.tipo == TipoEvento.FIN)
  ids = sorted(f"P{i}" for i in range(1, 11))
  assert arribos == ids
  assert fines == ids
  tiempos = [b.tiempo for b in corrida.bloques]
  assert tiempos == sorted(set(tiempos))  # un bloque por instante, en orden


def test_arribos_simultaneos_se_agrupan_en_un_bloque_por_id():
  corrida = Corrida([proceso("P3", 1, 0), proceso("P1", 1, 0), proceso("P2", 1, 0)])

  assert eventos(corrida.bloques[0]) == [
    (TipoEvento.ARRIBO, "P1"), (TipoEvento.ARRIBO, "P2"), (TipoEvento.ARRIBO, "P3"),
  ]


def test_fin_y_arribo_en_el_mismo_instante_comparten_bloque():
  corrida = Corrida([proceso("P1", 2, 0), proceso("P2", 1, 2)])

  assert eventos(corrida.bloque(2)) == [(TipoEvento.FIN, "P1"), (TipoEvento.ARRIBO, "P2")]
  assert len(corrida.bloques) == 3


def test_solo_arribos_y_fines_disparan_bloques():
  corrida = Corrida(CASO_LIBRO)

  tipos = {e.tipo for b in corrida.bloques for e in b.eventos}
  assert tipos == {TipoEvento.ARRIBO, TipoEvento.FIN}
  assert any(e.tipo == TipoEvento.DESALOJO for e in corrida.motor.eventos)


def test_cada_bloque_muestra_t_y_eventos_con_id():
  corrida = Corrida(CASO_LIBRO)

  lineas = corrida.texto(5).splitlines()
  assert lineas[0] == "========== t = 5 =========="
  assert lineas[1] == "FIN     P2"


def test_espera_al_usuario_despues_de_cada_bloque():
  registro: list[str] = []
  motor = crear_motor_srtf(CASO_LIBRO)
  bloques = ejecutar_pausas(
    motor,
    salida=lambda _texto: registro.append("bloque"),
    esperar=lambda prompt: registro.append(prompt),
  )

  assert registro == ["bloque", PROMPT] * (len(bloques) - 1) + ["bloque", PROMPT_FINAL]


def test_entrada_cerrada_interrumpe_sin_seguir_simulando():
  def entrada_cerrada(_prompt: str) -> None:
    raise EOFError

  salidas: list[str] = []
  motor = crear_motor_srtf(CASO_LIBRO)
  bloques = ejecutar_pausas(motor, salida=salidas.append, esperar=entrada_cerrada)

  assert len(bloques) == 1
  assert salidas[-1] == "Entrada cerrada, simulación interrumpida"
  assert not motor.terminado


# ---------- HU-14: estado del procesador ----------

def test_prueba_tecnica_cpu_coincide_con_calculo_a_mano():
  corrida = Corrida(CASO_LIBRO)

  esperado = {
    0: "CPU: P1 (restante 8)",
    1: "CPU: P2 (restante 4)",
    2: "CPU: P2 (restante 3)",
    3: "CPU: P2 (restante 2)",
    5: "CPU: P4 (restante 5)",
    10: "CPU: P1 (restante 7)",
    17: "CPU: P3 (restante 9)",
    26: "CPU ociosa",
  }
  assert {b.tiempo: corrida.linea_cpu(b.tiempo) for b in corrida.bloques} == esperado


def test_cpu_ociosa_mientras_no_hay_procesos():
  corrida = Corrida([proceso("P1", 2, 0), proceso("P2", 1, 5)])

  assert corrida.linea_cpu(2) == "CPU ociosa"
  assert corrida.linea_cpu(5) == "CPU: P2 (restante 1)"


def test_desalojo_indica_desalojado_y_reemplazo():
  corrida = Corrida(CASO_LIBRO)

  assert "Desalojo: P1 fue desalojado por P2" in corrida.texto(1).splitlines()
  otros = [s for b, s in zip(corrida.bloques, corrida.salidas) if b.tiempo != 1]
  assert not any("Desalojo" in s for s in otros)


# ---------- HU-15: tabla de particiones ----------

def test_prueba_tecnica_tabla_tras_best_fit_y_fusion():
  """t=3 termina P1 (hueco de 150K); t=7 termina P2, su hueco se fusiona con el de P1
  (300K) y PG (250K) sale de Listo/Suspendido con Best-Fit dejando 50K libres."""
  motor = crear_motor_srtf([
    proceso("P1", 3, 0, tamano=150),
    proceso("P2", 4, 0, tamano=150),
    proceso("P3", 10, 0, tamano=150),
    proceso("PG", 6, 0, tamano=250),
  ])

  avanzar_hasta(motor, 3)
  assert filas_memoria(motor) == [
    ("0", "0K", "100K", "OCUPADA", "SO"),
    ("1", "100K", "150K", "LIBRE", "Libre"),
    ("2", "250K", "150K", "OCUPADA", "P2"),
    ("3", "400K", "150K", "OCUPADA", "P3"),
  ]

  avanzar_hasta(motor, 7)
  assert filas_memoria(motor) == [
    ("0", "0K", "100K", "OCUPADA", "SO"),
    ("1", "100K", "250K", "OCUPADA", "PG"),
    ("4", "350K", "50K", "LIBRE", "Libre"),
    ("3", "400K", "150K", "OCUPADA", "P3"),
  ]
  assert resumen_memoria(motor) == (550, 50, 50)
  assert formatear_memoria(motor)[-1] == (
    "  Total: 550K  Memoria libre: 50K  Mayor hueco disponible: 50K"
  )


def test_tabla_ordenada_por_inicio_suma_550_e_incluye_so_en_cada_evento():
  corrida = Corrida(leer_procesos("pruebas/10_procesos.txt"))

  assert len(corrida.memorias) == len(corrida.bloques)
  for filas in corrida.memorias:
    inicios = [int(f[1].removesuffix("K")) for f in filas]
    tamanos = [int(f[2].removesuffix("K")) for f in filas]
    assert inicios == sorted(inicios)
    assert sum(tamanos) == 550
    assert filas[0] == ("0", "0K", "100K", "OCUPADA", "SO")


def test_huecos_marcados_libres_con_total_y_mayor_hueco():
  motor = crear_motor_srtf([proceso("P1", 3, 0, tamano=120), proceso("P2", 9, 0, tamano=60)])
  avanzar_hasta(motor, 3)  # termina P1: hueco de 120K + hueco final de 270K

  libres = [f for f in filas_memoria(motor) if f[3] == "LIBRE"]
  assert [(f[1], f[2], f[4]) for f in libres] == [
    ("100K", "120K", "Libre"), ("280K", "270K", "Libre"),
  ]
  assert formatear_memoria(motor)[1].split() == ["Id", "Inicio", "Tamaño", "Estado", "Proceso"]
  assert resumen_memoria(motor) == (550, 390, 270)


# ---------- HU-16: colas ----------

def test_colas_muestran_ids_restante_nuevo_y_contador():
  motor = crear_motor_srtf(SIMULTANEOS)
  motor.procesar_instante()

  assert formatear_colas(motor) == [
    "Colas:",
    "  Listo: P2(2), P3(3), P4(4)",
    "  Listo/Suspendido: P5(5)",
    "  Nuevo: P6(6), P7(7)",
    "  Por arribar: (vacío)",
    "  Terminados: (vacío)",
    "  Grado de multiprogramación: 5/5   (Ejecución 1 + Listo 3 + Listo/Suspendido 1)",
  ]


def test_listo_se_muestra_por_prioridad_srtf():
  motor = crear_motor_srtf(CASO_LIBRO)
  avanzar_hasta(motor, 3)

  assert [p.id for p in motor.colas.listo] == ["P1", "P3", "P4"]  # orden interno
  assert "  Listo: P4(5), P1(7), P3(9)" in formatear_colas(motor)


def test_colas_vacias_y_pendientes_de_arribo():
  motor = crear_motor_srtf(CASO_LIBRO)
  motor.procesar_instante()

  colas = formatear_colas(motor)
  assert "  Listo: (vacío)" in colas
  assert "  Listo/Suspendido: (vacío)" in colas
  assert "  Nuevo: (vacío)" in colas
  assert "  Por arribar: P2(arribo 1), P3(arribo 2), P4(arribo 3)" in colas


def test_terminados_con_instante_de_finalizacion():
  motor = crear_motor_srtf(CASO_LIBRO)
  avanzar_hasta(motor, 10)

  assert "  Terminados: P2(t=5), P4(t=10)" in formatear_colas(motor)


@pytest.mark.parametrize("procesos", [
  leer_procesos("pruebas/10_procesos.txt"),
  SIMULTANEOS,
], ids=["10_procesos", "simultaneos"])
def test_prueba_tecnica_contador_nunca_supera_5(procesos):
  corrida = Corrida(procesos)

  contadores = [
    int(m) for s in corrida.salidas
    for m in re.findall(r"Grado de multiprogramación: (\d+)/5", s)
  ]
  assert len(contadores) == len(corrida.bloques)
  assert max(contadores) == GRADO_MAXIMO


# ---------- HU-17: informe final ----------

def test_prueba_tecnica_informe_caso_de_libro():
  corrida = Corrida(CASO_LIBRO)

  filas = filas_informe(corrida.motor)
  assert filas == [
    ("P1", 0, 8, 17, 17, 9),
    ("P2", 1, 4, 5, 4, 0),
    ("P3", 2, 9, 26, 24, 15),
    ("P4", 3, 5, 10, 7, 2),
  ]
  assert sum(f[5] for f in filas) / len(filas) == 6.5


def test_informe_cumple_formulas_y_no_tiene_negativos():
  corrida = Corrida(leer_procesos("pruebas/10_procesos.txt"))

  filas = filas_informe(corrida.motor)
  assert [f[0] for f in filas] == [f"P{i}" for i in range(1, 11)]  # orden natural de Id
  for _id, arribo, irrupcion, fin, retorno, espera in filas:
    assert retorno == fin - arribo
    assert espera == retorno - irrupcion
    assert retorno >= irrupcion > 0
    assert espera >= 0


def test_informe_texto_con_encabezado_y_formulas():
  corrida = Corrida(CASO_LIBRO)

  lineas = formatear_informe(corrida.motor).splitlines()
  assert lineas[0] == "========== Informe final =========="
  assert lineas[1].split() == ["Id", "Arribo", "Irrupción", "Finalización", "Retorno", "Espera"]
  assert lineas[2].split() == ["P1", "0", "8", "17", "17", "9"]
  assert "Retorno = Finalización - Arribo | Espera = Retorno - Irrupción" in lineas


def test_informe_solo_se_genera_con_todos_terminados():
  motor = crear_motor_srtf(CASO_LIBRO)
  avanzar_hasta(motor, 10)

  with pytest.raises(ErrorReporte, match="todos los procesos terminaron"):
    filas_informe(motor)
  with pytest.raises(ErrorReporte):
    formatear_informe(motor)


def test_informe_rechaza_valores_negativos():
  corrida = Corrida(CASO_LIBRO)
  corrida.motor.colas.terminado[0].finalizacion = -1

  with pytest.raises(ErrorReporte, match="negativos"):
    filas_informe(corrida.motor)


# ---------- HU-18: promedios y throughput ----------

@pytest.mark.parametrize(("procesos", "retorno", "espera", "throughput", "texto"), [
  # Retornos 17+4+24+7=52, esperas 9+0+15+2=26, 4 procesos de t=0 a t=26.
  (CASO_LIBRO, 13.0, 6.5, 4 / 26, ("13.00", "6.50", "0.15", 4, 26, 0, 26)),
  # Retornos 18+2+11+4+20+1+5=61, esperas 12+0+7+1+15+0+3=38, 7 procesos de t=0 a t=23.
  (leer_procesos("pruebas/tutorial.txt"), 61 / 7, 38 / 7, 7 / 23,
   ("8.71", "5.43", "0.30", 7, 23, 0, 23)),
  # Retornos suman 194, esperas 145, 10 procesos de t=0 a t=49.
  (leer_procesos("pruebas/10_procesos.txt"), 19.4, 14.5, 10 / 49,
   ("19.40", "14.50", "0.20", 10, 49, 0, 49)),
], ids=["libro", "tutorial", "10_procesos"])
def test_prueba_tecnica_promedios_y_throughput_calculados_a_mano(
  procesos, retorno, espera, throughput, texto
):
  corrida = Corrida(procesos)

  metricas = calcular_metricas(corrida.motor)
  assert metricas.retorno_medio == pytest.approx(retorno)
  assert metricas.espera_media == pytest.approx(espera)
  assert metricas.throughput == pytest.approx(throughput)

  r, e, th, n, base, inicio, fin = texto
  assert formatear_informe(corrida.motor).splitlines()[-4:] == [
    f"Retorno medio: {r} u.t.",
    f"Espera media: {e} u.t.",
    f"Throughput: {th} procesos/u.t. ({n} procesos en {base} u.t., de t={inicio} a t={fin})",
    "Throughput = terminados / (fin del último - primer arribo)",
  ]


def test_throughput_se_mide_desde_el_primer_arribo():
  """Supuesto 10: el tiempo previo al primer arribo no cuenta (2/4, no 2/6)."""
  corrida = Corrida([proceso("P1", 3, 2), proceso("P2", 1, 5)])

  metricas = calcular_metricas(corrida.motor)
  assert (metricas.inicio, metricas.fin, metricas.tiempo_base) == (2, 6, 4)
  assert metricas.throughput == 0.5
  assert "Throughput: 0.50 procesos/u.t. (2 procesos en 4 u.t., de t=2 a t=6)" in (
    formatear_informe(corrida.motor)
  )


def test_metricas_solo_con_todos_terminados():
  motor = crear_motor_srtf(CASO_LIBRO)
  avanzar_hasta(motor, 10)

  with pytest.raises(ErrorReporte):
    calcular_metricas(motor)
