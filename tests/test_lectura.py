import pytest

from simulador.lectura import ErrorLectura, Proceso, leer_procesos

PROCESOS_10 = [
  Proceso("P1", 120, 0, 8),
  Proceso("P2", 60, 1, 4),
  Proceso("P3", 200, 2, 9),
  Proceso("P4", 90, 3, 5),
  Proceso("P5", 30, 4, 3),
  Proceso("P6", 150, 5, 7),
  Proceso("P7", 45, 6, 2),
  Proceso("P8", 80, 7, 6),
  Proceso("P9", 110, 8, 4),
  Proceso("P10", 25, 9, 1),
]

def crear_archivo(tmp_path, contenido): 
  ruta = tmp_path / "procesos.txt"
  ruta.write_text(contenido, encoding="utf-8")
  return str(ruta)

def test_lee_un_proceso(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,120,0,8\n")
  procesos = leer_procesos(ruta)

  assert procesos == [Proceso("P1", 120, 0, 8)]

def test_archivo_inexistente(tmp_path):
  with pytest.raises(ErrorLectura, match="no existe"):
    leer_procesos(str(tmp_path / "nada.txt"))

def test_archivo_vacio(tmp_path):
  ruta = crear_archivo(tmp_path, "")
  with pytest.raises(ErrorLectura, match="no contiene procesos"):
    leer_procesos(ruta)

def test_linea_con_tres_campos(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,120,0,8\nP2,60,1\n")
  with pytest.raises(ErrorLectura, match="Línea 2"):
    leer_procesos(ruta)

def test_campo_no_numerico(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,abc,0,8\n")
  with pytest.raises(ErrorLectura, match="Línea 1"):
    leer_procesos(ruta)

def test_ignora_espacios_y_comentarios(tmp_path):
  contenido = "# encabezado\n\n P1, 120 , 0 , 8 \n\nP2,60,1,4\n"
  ruta = crear_archivo(tmp_path, contenido)

  procesos = leer_procesos(ruta)

  assert procesos == [Proceso("P1", 120, 0, 8), Proceso("P2", 60, 1, 4)]

def test_carga_10_procesos_con_coincidencia(tmp_path):
  lineas = [f"{p.id},{p.tamano},{p.arribo},{p.irrupcion}" for p in PROCESOS_10]
  ruta = crear_archivo(tmp_path, "\n".join(lineas) + "\n")

  procesos = leer_procesos(ruta)

  assert len(procesos) == 10
  for leido, esperado in zip(procesos, PROCESOS_10):
    assert leido.id == esperado.id
    assert leido.tamano == esperado.tamano
    assert leido.arribo == esperado.arribo
    assert leido.irrupcion == esperado.irrupcion

def test_carga_10_procesos_real():
  procesos = leer_procesos("pruebas/10_procesos.txt")

  assert procesos == PROCESOS_10
