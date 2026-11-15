"""HU-05 (asignación Best-Fit) y HU-06 (liberación y fusión de huecos)."""

import pytest

from simulador.memoria import ID_SO, ErrorMemoria, EstadoParticion, Memoria


def armar(*bloques: tuple[str, int]) -> Memoria:
  """Ocupa la memoria de usuario con bloques contiguos, en orden, desde 100K."""
  memoria = Memoria()
  for id_proceso, tamano in bloques:
    assert memoria.asig_bestfit(tamano, id_proceso) is not None
  return memoria


def liberar(memoria: Memoria, *ids_proceso: str) -> None:
  for id_proceso in ids_proceso:
    particion = next(p for p in memoria.particiones if p.proceso == id_proceso)
    memoria.liberar(particion.id)


def mapa(memoria: Memoria) -> list[tuple[int, int, str | None]]:
  return [(p.inicio, p.tamano, p.proceso) for p in memoria.particiones]


# ---------- HU-05: Best-Fit ----------

def test_prueba_tecnica_proceso_de_35_va_al_hueco_de_40():
  """Huecos de 60K, 40K y 100K: un proceso de 35K se asigna al de 40K."""
  memoria = armar(("A", 60), ("B", 10), ("C", 40), ("D", 10), ("E", 100), ("F", 230))
  liberar(memoria, "A", "C", "E")
  assert [(h.inicio, h.tamano) for h in memoria.huecos()] == [(100, 60), (170, 40), (220, 100)]

  particion = memoria.asig_bestfit(35, "P")

  assert (particion.inicio, particion.tamano, particion.proceso) == (170, 35, "P")
  assert [(h.inicio, h.tamano) for h in memoria.huecos()] == [
    (100, 60), (205, 5), (220, 100),
  ]
  memoria.verificar_invariante()


def test_elige_el_hueco_mas_chico_aunque_este_al_final():
  memoria = armar(("A", 100), ("B", 10), ("C", 30))  # hueco libre final de 310K
  liberar(memoria, "A", "C")  # C se fusiona con el hueco final: 340K
  assert memoria.mejor_hueco(90).inicio == 100


def test_empate_de_tamano_elige_menor_direccion():
  memoria = armar(("A", 50), ("B", 10), ("C", 50), ("D", 340))
  liberar(memoria, "C", "A")

  particion = memoria.asig_bestfit(30, "P")

  assert particion.inicio == 100


def test_hueco_exacto_no_deja_remanente():
  memoria = armar(("A", 60), ("B", 390))
  liberar(memoria, "A")

  memoria.asig_bestfit(60, "P")

  assert memoria.huecos() == []
  assert mapa(memoria) == [(0, 100, "SO"), (100, 60, "P"), (160, 390, "B")]


def test_sin_hueco_suficiente_devuelve_none_sin_modificar_la_memoria():
  """La suma de huecos alcanza (100K) pero ningún hueco individual: no hay compactación."""
  memoria = armar(("A", 50), ("B", 200), ("C", 50), ("D", 150))
  liberar(memoria, "A", "C")
  antes = mapa(memoria)

  assert memoria.mejor_hueco(80) is None
  assert memoria.asig_bestfit(80, "P") is None
  assert mapa(memoria) == antes


# ---------- HU-06: liberación y fusión ----------

def test_liberar_sin_vecinos_libres_solo_marca_libre():
  memoria = armar(("A", 100), ("B", 100), ("C", 250))
  liberar(memoria, "B")

  assert mapa(memoria) == [(0, 100, "SO"), (100, 100, "A"), (200, 100, None), (300, 250, "C")]
  assert memoria.particiones[2].estado == EstadoParticion.LIBRE


def test_fusiona_con_hueco_anterior():
  memoria = armar(("A", 100), ("B", 100), ("C", 250))
  liberar(memoria, "A", "B")

  assert mapa(memoria) == [(0, 100, "SO"), (100, 200, None), (300, 250, "C")]


def test_fusiona_con_hueco_posterior():
  memoria = armar(("A", 100), ("B", 100))  # hueco final de 250K
  liberar(memoria, "B")

  assert mapa(memoria) == [(0, 100, "SO"), (100, 100, "A"), (200, 350, None)]


def test_prueba_tecnica_liberar_proceso_central_entre_dos_huecos():
  """Liberar el proceso central deja un único hueco con la suma de los tres."""
  memoria = armar(("A", 100), ("B", 120), ("C", 80), ("D", 150))
  liberar(memoria, "A", "C")
  assert len(memoria.huecos()) == 2

  liberar(memoria, "B")

  assert mapa(memoria) == [(0, 100, "SO"), (100, 300, None), (400, 150, "D")]
  memoria.verificar_invariante()


def test_liberar_todo_vuelve_al_estado_inicial():
  memoria = armar(("A", 100), ("B", 120), ("C", 80), ("D", 150))
  liberar(memoria, "C", "A", "D", "B")

  assert mapa(memoria) == [(0, 100, "SO"), (100, 450, None)]


def test_particion_del_so_nunca_se_libera_ni_se_fusiona():
  memoria = armar(("A", 100), ("B", 350))
  with pytest.raises(ErrorMemoria):
    memoria.liberar(ID_SO)

  liberar(memoria, "A")  # hueco adyacente al SO

  so = memoria.particiones[0]
  assert (so.id, so.inicio, so.tamano, so.proceso) == (ID_SO, 0, 100, "SO")
  assert memoria.particiones[1].inicio == 100


def test_liberar_particion_libre_o_inexistente_falla():
  memoria = armar(("A", 100))
  hueco = memoria.huecos()[0]
  with pytest.raises(ErrorMemoria, match="ya está libre"):
    memoria.liberar(hueco.id)
  with pytest.raises(ErrorMemoria, match="No existe"):
    memoria.liberar(99)
