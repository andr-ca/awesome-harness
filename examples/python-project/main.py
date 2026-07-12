"""Trivial placeholder — this fixture exists to verify harness integration
against a realistic Python project layout, not to demonstrate application
code."""


def main() -> int:
    print("python-project fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
