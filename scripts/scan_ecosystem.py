"""Scan every distinct installed package for phantom docstring parameters.

The repo's published finding is 101 phantom parameters across **eight**
libraries. Eight is a sample of an unbounded corpus, and a sample of a *count*
can only undercount — so the real question the repo cannot currently answer is
what the ecosystem rate is.

This collects every top-level package across the venvs already on disk, keeps
one copy of each by name, and scans them all. Nothing is downloaded.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"D:\github\docstring-drift\src")
from drift import scan_path  # noqa: E402

ROOT = Path(r"D:\github")
SKIP_PREFIX = ("_", ".")
SKIP_EXACT = {"tests", "test", "__pycache__", "site-packages", "bin", "share",
              "include", "etc", "Scripts", "lib", "lib64"}

# One directory per package name — the first venv that has it wins, so a
# package installed in twelve venvs is counted once, not twelve times.
seen: dict[str, Path] = {}
for sp in ROOT.glob("*/.venv/Lib/site-packages"):
    if not sp.is_dir():
        continue
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

print(f"{len(seen)} distinct packages found on disk", flush=True)

results = {}
totals = defaultdict(int)
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
            {"file": f.file, "line": f.line, "func": getattr(f, "func", ""),
             "param": getattr(f, "param", "")}
            for f in findings if f.kind == "phantom"
        ][:40],
    }
    for k, v in stats.items():
        totals[k] += v
    if stats["phantom"]:
        print(f"  [{i}/{len(seen)}] {name:<28} {stats['functions']:>7} fns  "
              f"{stats['phantom']:>3} phantom", flush=True)

out = Path(__file__).resolve().parent / "scan_many.json"
out.write_text(json.dumps({"totals": dict(totals), "packages": results}, indent=1),
               encoding="utf-8")

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
