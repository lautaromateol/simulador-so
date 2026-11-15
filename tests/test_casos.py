"""HU-19: cada caso de `pruebas/` coincide con su salida esperada calculada a mano."""

from pathlib import Path

import pytest

from simulador.lectura import leer_procesos
from simulador.motor import Motor
from simulador.pcb import Estado
from simulador.planificador import crear_motor_srtf
from simulador.reporte import formatear_informe

PRUEBAS = Path(__file__).resolve().parent.parent / "pruebas"
ESPERADOS = sorted((PRUEBAS / "esperado").glob("*.txt"))
PREFIJO_CPU = "# CPU: "


def simular(caso: Path) -> Motor:
  motor = crear_motor_srtf(leer_procesos(str(PRUEBAS / caso.name)))
  motor.ejecutar()
  return motor


def gantt(motor: Motor) -> str:
  """Tramos de CPU reconstruidos desde el historial de cada proceso."""
  tramos = [(inicio, fin, "ociosa") for inicio, fin in motor.ociosos]
  for pcb in motor.colas.terminado:
    desde = None
    for transicion in pcb.historial:
      if transicion.destino == Estado.EJECUCION:
        desde = transicion.tiempo
      elif transicion.origen == Estado.EJECUCION:
        tramos.append((desde, transicion.tiempo, pcb.id))
  return " | ".join(f"{inicio}-{fin} {quien}" for inicio, fin, quien in sorted(tramos))


def normalizar(lineas: list[str]) -> list[list[str]]:
  return [linea.split() for linea in lineas if linea.strip()]


def test_cada_archivo_de_prueba_tiene_su_salida_esperada():
  casos = {p.name for p in PRUEBAS.glob("*.txt")}
  assert casos == {p.name for p in ESPERADOS}
  assert len(casos) >= 5


@pytest.mark.parametrize("esperado", ESPERADOS, ids=[p.stem for p in ESPERADOS])
def test_informe_coincide_con_el_calculado_a_mano(esperado: Path):
  lineas = esperado.read_text(encoding="utf-8").splitlines()
  informe = [linea for linea in lineas if not linea.startswith("#")]

  motor = simular(esperado)

  assert normalizar(formatear_informe(motor).splitlines()) == normalizar(informe)


@pytest.mark.parametrize("esperado", ESPERADOS, ids=[p.stem for p in ESPERADOS])
def test_diagrama_de_cpu_coincide_con_el_calculado_a_mano(esperado: Path):
  lineas = esperado.read_text(encoding="utf-8").splitlines()
  cpu = next(linea for linea in lineas if linea.startswith(PREFIJO_CPU))

  motor = simular(esperado)

  assert gantt(motor) == cpu.removeprefix(PREFIJO_CPU)
