from dataclasses import dataclass

MAX_PROCESOS = 10
MEMORIA_USUARIO = 450

@dataclass(frozen=True)
class Proceso:
  id: str
  tamano: int
  arribo: int
  irrupcion: int

class ErrorLectura(Exception):
  """Error al abrir o leer el archivo de procesos."""

def leer_procesos(ruta: str) -> list[Proceso]:
  try: 
    with open(ruta, encoding="utf-8") as archivo:
      procesos = []
      numeros_linea = []
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
        numeros_linea.append(numero)
      if not procesos:
        raise ErrorLectura(f"El archivo '{ruta}' no contiene procesos")
      validar_procesos(procesos, numeros_linea)
      return procesos
  except FileNotFoundError:
    raise ErrorLectura(f"El archivo '{ruta}' no existe")
  except PermissionError: 
    raise ErrorLectura(f"Sin permisos para leer '{ruta}'")
  except UnicodeDecodeError:
    raise ErrorLectura(f"'{ruta}' no es un archivo de texto valido")

def validar_procesos(procesos: list[Proceso], numeros_linea: list[int]) -> None:
  errores = []
  if len(procesos) > MAX_PROCESOS:
    errores.append(
      f"El archivo tiene {len(procesos)}, el máximo es {MAX_PROCESOS}"
    )

  lineas_por_id = {}
  for proceso, numero in zip(procesos, numeros_linea):
    if proceso.id in lineas_por_id:
      errores.append(
        f"Línea {numero}: el Id '{proceso.id}' ya fue definido en la línea "
        f"{lineas_por_id[proceso.id]}"
      )
    else:
      lineas_por_id[proceso.id] = numero
    if proceso.tamano <= 0:
      errores.append(
        f"Línea {numero}: el proceso '{proceso.id}' debe tener Tamaño mayor que 0 (recibido: {proceso.tamano})"
      )
    elif proceso.tamano > MEMORIA_USUARIO:
      errores.append(
        f"Línea {numero}: el proceso '{proceso.id}' pide {proceso.tamano}K "
        f"y supera los {MEMORIA_USUARIO}K disponibles"
      )
    if proceso.irrupcion <= 0:
      errores.append(
        f"Línea {numero}: el proceso '{proceso.id}' debe tener Irrupción mayor que 0 (recibido: {proceso.irrupcion})"
      )
    if proceso.arribo < 0:
      errores.append(
        f"Línea {numero}: el proceso '{proceso.id}' debe tener Arribo mayor o igual que 0 (recibido: {proceso.arribo})"
      )
  if errores:
    raise ErrorLectura("\n".join(errores))
                