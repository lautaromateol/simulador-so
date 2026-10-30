import pytest
from tests.test_lectura import crear_archivo
from simulador.lectura import ErrorLectura, leer_procesos

def generar_lineas(cantidad): 
  return "".join(f"P{i},10,{i},5\n" for i in range(1, cantidad + 1))

def test_acepta_10_procesos(tmp_path):
  ruta = crear_archivo(tmp_path, generar_lineas(10))
  assert len(leer_procesos(ruta)) == 10

def test_rechaza_11_procesos(tmp_path):
  ruta = crear_archivo(tmp_path, generar_lineas(11))
  with pytest.raises(ErrorLectura, match="el máximo es 10"):
    leer_procesos(ruta)

def test_rechaza_tamano_cero(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,0,0,5\n")
  with pytest.raises(ErrorLectura, match="Línea 1.*Tamaño"):
    leer_procesos(ruta)

def test_rechaza_arribo_negativo(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,10,-5,5\n")
  with pytest.raises(ErrorLectura, match="Línea 1.*Arribo"):
    leer_procesos(ruta)

def test_acepta_arribo_cero(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,10,0,5\n")
  assert len(leer_procesos(ruta)) == 1

def test_rechaza_irrupcion_cero(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,10,0,0")
  with pytest.raises(ErrorLectura, match="Línea 1.*Irrupción"):
    leer_procesos(ruta)

def test_rechaza_id_duplicado(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,10,0,5\nP2,20,1,5\nP1,30,2,5\n")
  with pytest.raises(ErrorLectura, match="Línea 3.*'P1'.*línea 1"):
    leer_procesos(ruta)

def test_acepta_tamano_450(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,450,0,5\n")
  assert len(leer_procesos(ruta)) == 1

def test_rechaza_tamano_451(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,10,0,5\nP2,451,1,5\n")
  with pytest.raises(ErrorLectura, match="Línea 2.*450K"):
    leer_procesos(ruta)

def test_informa_todos_los_errores_juntos(tmp_path):
  ruta = crear_archivo(tmp_path, "P1,0,0,5\nP2,10,-3,5\n")
  with pytest.raises(ErrorLectura) as info:
    leer_procesos(ruta)
  mensaje = str(info.value)
  assert "Línea 1" in mensaje
  assert "Línea 2" in mensaje