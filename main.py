import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador MVT Best-Fit + SRTF")
    parser.add_argument("--input", required=True, help="Archivo de procesos (CSV/txt)")
    parser.parse_args()


if __name__ == "__main__":
    main()
