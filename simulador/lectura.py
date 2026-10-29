from typing import List 
from dataclasses import dataclass

@dataclass(frozen=True)
class Proceso:
  id: str
  tamano: int
  arribo: int
  irrupcion: int

class ErrorLectura(Exception):
  """Error al abrir o leer el archivo de procesos."""

def leer_procesos(ruta: str) -> List[Proceso]:
  try: 
    with open(ruta, encoding="utf-8") as archivo:
      procesos = []
      for numero, linea in enumerate(archivo, start=1):
        linea = linea.strip()
        if linea == "" or linea.startswith("#"):
          continue
        partes = [p.strip() for p in linea.split(",")]
        if len(partes) != 4:
            raise ErrorLectura(
              f"Línea {numero}: se esperaban 4 campos y hay {len(partes)}"
            )
        id_proceso, texto_tam, texto_arribo, texto_irrup = partes
        try:
          tamano = int(texto_tam)
          arribo = int(texto_arribo)
          irrupcion = int(texto_irrup)
        except ValueError:
          raise ErrorLectura(
            f"Línea {numero}: Tamaño, Arribo e Irrupción deben ser números enteros"
          )
        procesos.append(Proceso(id_proceso, tamano, arribo, irrupcion))
      if not procesos:
        raise ErrorLectura(f"El archivo '{ruta}' no contiene procesos")
      return procesos
  except FileNotFoundError:
    raise ErrorLectura(f"El archivo '{ruta}' no existe")
  except PermissionError: 
    raise ErrorLectura(f"Sin permisos para leer '{ruta}'")
  except UnicodeDecodeError:
    raise ErrorLectura(f"'{ruta}' no es un archivo de texto valido")