# Results

[<- back to README](../README.md)

Every number on this page and in the README headline comes from one file,
[`results/ecosystem-scan.json`](../results/ecosystem-scan.json), which is the raw output of
`scripts/scan_ecosystem.py` — nothing here is estimated or hand-adjusted.

## The headline

**517 phantom parameters across 161 Python packages — 1.93% of every function that
documents its parameters (517 / 26,856).**

| | |
|---|---:|
| Packages scanned | **161** |
| Files | 20,607 |
| Functions | 326,832 |
| Functions documenting parameters | 26,856 |
| **Phantom** | **517** |
| Undocumented | 20,050 |

**45 of 161 packages carry at least one phantom.** The rest are clean — this is not a rate
that applies everywhere.

## Top 10 by phantom count

| Package | functions | documenting params | **phantom** |
|---|---:|---:|---:|
| transformers | 35,432 | 2,740 | **105** |
| torch | 42,608 | 2,183 | **105** |
| sympy | 35,561 | 1,361 | **52** |
| networkx | 7,207 | 1,076 | **49** |
| pandas | 28,295 | 1,631 | **40** |
| scipy | 24,004 | 1,872 | **19** |
| fontTools | 5,524 | 155 | **12** |
| rich | 912 | 265 | **10** |
| websockets · scikit-learn · sentence-transformers | 13,448 | 1,965 | **27** |
| numpy | 11,215 | 732 | **8** |

The full per-package breakdown (all 161) is in
[`results/ecosystem-scan.json`](../results/ecosystem-scan.json) — every package's own
`stats`, plus up to 40 of its phantom findings with file, line, function and parameter
name.

## A verified example

`pandas/_testing/_io.py`, `round_trip_pickle`:

```python
def round_trip_pickle(obj, tmp_path):     # <- the parameter is tmp_path
    """
    Pickle an object and then read it again.

    Parameters
    ----------
    obj : any object
        The object to pickle and then re-read.
    path : str, path object or file-like object, default None    # <- documents `path`
        The path where the pickled object is written and then read.
    """
```

The parameter was renamed to `tmp_path`; the docstring still documents `path`. This was
checked by hand against the real source **before** any number here was published, because
the first version of the scanner produced findings that looked publishable and were not —
see [PROBLEMS.md](PROBLEMS.md).

## Reproducing this

`scripts/scan_ecosystem.py` takes no hardcoded paths — it scans whatever site-packages
directories you point it at (or, with no arguments, the current interpreter's own):

```bash
# Scan whatever is installed in your active environment right now:
python scripts/scan_ecosystem.py

# Scan a single package's installed source directly:
python src/drift.py path/to/site-packages/pandas

# Reproduce the ecosystem-wide shape of the headline: point it at a directory that
# holds several unrelated projects' venvs (this is exactly how 517/161 was produced —
# by scanning every venv living side by side in one multi-repo workspace):
python scripts/scan_ecosystem.py /path/to/many/repos -o results/ecosystem-scan.json
```

**Exact counts depend on which package versions happen to be installed** (see
[LIMITATIONS.md](LIMITATIONS.md)) — a fresh run against different versions, or a
differently-populated workspace, will not reproduce 517/161 to the digit. What *is*
reproducible is the method: the same command, run against your own installed packages,
measures the same thing the same way and writes the same shape of report.

There is no dashboard or UI in this repo — `results/ecosystem-scan.json` and this page are
the whole of "the results."

## An earlier, smaller pass

Before scanning 161 packages, the first published number was **101 phantom parameters
across 8 packages** (that run's output is [`results/scan.json`](../results/scan.json)).
Scanning 161 packages instead of 8 raised the raw count to 956 — and then reading the
findings showed 53% of them were docstring section headers, not parameters, which is the
false-positive class described in the README and fixed in `src/drift.py`'s `STOP` pattern.
517 is the number after that fix; the two runs are not directly comparable.
