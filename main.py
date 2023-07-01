import argparse

from compiler import program


def main() -> None:
    parser = argparse.ArgumentParser(description='Compiler demo program (msil)')
    parser.add_argument('src', type=str, help='source code file')
    parser.add_argument('--msil-only', default=False, action='store_true', help='print only msil code (no ast)')
    args = parser.parse_args()

    with open(args.src, mode='r', encoding="utf-8") as f:
        src = f.read()

    program.execute(src, args.msil_only, file_name=args.src)


if __name__ == "__main__":
    main()
