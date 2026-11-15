import argparse
import sys

from simulador.lectura import ErrorLectura, leer_procesos
from simulador.planificador import crear_motor_srtf
from simulador.reporte import ejecutar_pausas, formatear_informe


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador MVT Best-Fit + SRTF")
    parser.add_argument("--input", required=True, help="Archivo de procesos (CSV/txt)")
    args = parser.parse_args()

    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")

    try:
        procesos = leer_procesos(args.input)
    except ErrorLectura as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    motor = crear_motor_srtf(procesos)
    try:
        ejecutar_pausas(motor)
    except KeyboardInterrupt:
        print("\nSimulación interrumpida por el usuario")
        sys.exit(130)

    if motor.terminado:
        print(formatear_informe(motor))


if __name__ == "__main__":
    main()
