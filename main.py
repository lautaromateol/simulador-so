import argparse
import sys 
from simulador.lectura import leer_procesos, ErrorLectura

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador MVT Best-Fit + SRTF")
    parser.add_argument("--input", required=True, help="Archivo de procesos (CSV/txt)")
    args = parser.parse_args()

    try:
        procesos = leer_procesos(args.input)
    except ErrorLectura as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for p in procesos:
        print(p)


if __name__ == "__main__":
    main()
