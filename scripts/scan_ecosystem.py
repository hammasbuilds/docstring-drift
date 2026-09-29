"""Scan every distinct installed package across one or more environments for
phantom docstring parameters.

The repo's headline number (517 phantom parameters across 161 packages) was
produced by pointing this at a directory holding several dozen unrelated
projects' venvs, so that a package installed in twelve of them is counted
once, not twelve times. That directory is specific to the machine that ran
it, so the path is never hardcoded here - it is given on the command line.

Zero arguments: scans the site-packages of whichever Python is running this
script. That always works, on any machine, with nothing to configure:

    python scripts/scan_ecosystem.py

One or more paths: each is either a site-packages directory itself, or a
directory that *contains* venvs (anything matching `*/.venv/.../site-packages`
underneath it) - the shape of a multi-repo workspace:

    python scripts/scan_ecosystem.py D:\\path\\to\\many\\repos
    python scripts/scan_ecosystem.py .venv-ecosystem/Lib/site-packages

Nothing is downloaded; only what is already installed on disk is scanned. See
docs/RESULTS.md for the exact command (with a pinned package list) that
reproduces the published 517/161 figures.
"""

from __future__ import annotations

import argparse
import json
import site
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from drift import scan_path

SKIP_PREFIX = ("_", ".")
SKIP_EXACT = {
    "tests",
    "test",
    "__pycache__",
    "site-packages",
    "bin",
    "share",
    "include",
    "etc",
    "Scripts",
    "lib",
    "lib64",
}


def find_site_packages_dirs(roots: list[Path]) -> list[Path]:
    """Every `site-packages` directory reachable from the given roots.

    A root is either a site-packages directory itself, or a directory holding
    one or more venvs one level down (Windows `.venv/Lib/site-packages` and
    POSIX `.venv/lib/pythonX.Y/site-packages`, both directly and nested one
    level under `root` - e.g. `root/some-project/.venv/...`).
    """
    found: list[Path] = []
    for root in roots:
        if root.name == "site-packages" and root.is_dir():
            found.append(root)
            continue
        patterns = (
            ".venv/Lib/site-packages",
            ".venv/lib/python*/site-packages",
            "*/.venv/Lib/site-packages",
            "*/.venv/lib/python*/site-packages",
        )
        for pattern in patterns:
            found.extend(p for p in root.glob(pattern) if p.is_dir())
    return found


def collect_packages(site_packages_dirs: list[Path]) -> dict[str, Path]:
    """One directory per distinct top-level package name.

    The first environment that has a given name wins, so a package installed
    in many environments is counted once, not once per environment.
    """
    seen: dict[str, Path] = {}
    for sp in site_packages_dirs:
        for d in sp.iterdir():
            if not d.is_dir():
                continue
            name = d.name
            if name.startswith(SKIP_PREFIX) or name in SKIP_EXACT:
                continue
            if name.endswith((".dist-info", ".egg-info", ".data")):
                continue
            if name not in seen and any(d.rglob("*.py")):
                seen[name] = d
    return seen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "roots",
        nargs="*",
        help="site-packages dir(s), or dir(s) containing venvs. "
        "Default: this interpreter's own site-packages.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="where to write the JSON report (default: scripts/scan_many.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    roots = (
        [Path(r).resolve() for r in args.roots]
        if args.roots
        else [Path(p) for p in site.getsitepackages() if Path(p).is_dir()]
    )
    site_packages_dirs = find_site_packages_dirs(roots)
    if not site_packages_dirs:
        print(f"error: no site-packages directories found under {roots}", file=sys.stderr)
        return 2

    seen = collect_packages(site_packages_dirs)
    print(
        f"{len(seen)} distinct packages found across {len(site_packages_dirs)} environment(s)",
        flush=True,
    )

    results = {}
    totals: dict[str, int] = defaultdict(int)
    for i, (name, path) in enumerate(sorted(seen.items()), 1):
        try:
            findings, stats = scan_path(path)
        except (OSError, RecursionError, MemoryError) as exc:
            print(f"  [{i}/{len(seen)}] {name}: skipped ({type(exc).__name__})", flush=True)
            continue
        if not stats["functions"]:
            continue
        results[name] = {
            "stats": stats,
            "phantom": [
                {"file": f.file, "line": f.line, "func": f.function, "param": f.name}
                for f in findings
                if f.kind == "phantom"
            ][:40],
        }
        for k, v in stats.items():
            totals[k] += v
        if stats["phantom"]:
            print(
                f"  [{i}/{len(seen)}] {name:<28} {stats['functions']:>7} fns  "
                f"{stats['phantom']:>3} phantom",
                flush=True,
            )

    out = Path(args.output) if args.output else Path(__file__).resolve().parent / "scan_many.json"
    out.write_text(
        json.dumps({"totals": dict(totals), "packages": results}, indent=1), encoding="utf-8"
    )

    print()
    print("=" * 66)
    print(f"packages scanned      {len(results):>10,}")
    print(f"files                 {totals['files']:>10,}")
    print(f"functions             {totals['functions']:>10,}")
    print(f"with param docs       {totals['with_param_docs']:>10,}")
    print(f"PHANTOM               {totals['phantom']:>10,}")
    print(f"undocumented params   {totals['undocumented']:>10,}")
    if totals["with_param_docs"]:
        rate = totals["phantom"] / totals["with_param_docs"] * 100
        print(f"\nphantom rate: {rate:.2f}% of functions that document a parameter list")
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
