"""Run the scanner and show what it finds. No arguments, no setup, no network.

    python demo.py            # scan this repository
    python demo.py numpy      # scan an installed package by name
    python demo.py some/path  # scan a directory

Prints the counts and then the findings themselves, because a count nobody can
check is not evidence. Every line shown names the file, the line, the function,
and the parameter the docstring invented.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from drift import scan_path  # noqa: E402


def resolve(argument: str | None) -> Path:
    """A path, a package name, or the bundled examples.

    The default used to be this repository's own source, which is clean — so
    the demo printed "0 findings" and demonstrated nothing. It now scans
    `examples/`, which carries five deliberate drifts and one correct
    docstring as a control, so a first run always shows the tool working.
    """
    if not argument:
        return Path(__file__).resolve().parent / "examples"
    candidate = Path(argument)
    if candidate.exists():
        return candidate
    try:
        module = __import__(argument)
    except ImportError:
        raise SystemExit(
            f"'{argument}' is neither a path nor an importable package."
        ) from None
    where = getattr(module, "__file__", None)
    if not where:
        raise SystemExit(f"'{argument}' has no file on disk to scan.")
    return Path(where).parent


def main() -> None:
    target = resolve(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"scanning {target}\n")

    findings, stats = scan_path(target)
    phantom = [f for f in findings if f.kind == "phantom"]

    print(f"  files                        {stats['files']:>8,}")
    print(f"  functions                    {stats['functions']:>8,}")
    print(f"  documenting a parameter list {stats['with_param_docs']:>8,}")
    print(f"  PHANTOM                      {stats['phantom']:>8,}")
    print(f"  undocumented parameters      {stats['undocumented']:>8,}")

    if stats["with_param_docs"]:
        rate = stats["phantom"] / stats["with_param_docs"] * 100
        print(f"\n  phantom rate: {rate:.2f}% of functions that document parameters")

    if not phantom:
        print("\nNo phantom parameters here. Try: python demo.py transformers")
        return

    print(f"\n{'-' * 72}\nevery phantom finding:\n")
    for f in phantom[:40]:
        print(f"  {f.file}:{f.line}")
        print(f"    {f.describe()}")
    if len(phantom) > 40:
        print(f"\n  … and {len(phantom) - 40} more")


if __name__ == "__main__":
    main()
