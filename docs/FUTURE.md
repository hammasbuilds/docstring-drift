# Future work

[<- back to README](../README.md)

## 1. Check types, not just names

A docstring claiming `int` for a parameter annotated `str` is the same class of defect and
is detectable with the same AST pass. The most obvious next step.

## 2. Detect stale descriptions

A description that is no longer true is the most common form of documentation drift and
the least detectable. Names and types are comparable structurally; prose is not.

**This is where a language model would genuinely earn its place** - and it should be
measured against the deterministic checks rather than replacing them.

## 3. Recover recall on kwargs APIs

Catch-all signatures are currently exempt, so drift is invisible in exactly the libraries
most likely to have it. Following `**kwargs` to the function it is forwarded to would
close the gap without reintroducing the `einsum` false positive.

## 4. Returns and Raises sections

These drift too, and a documented exception that is no longer raised is arguably worse
than a stale parameter, because callers write `except` blocks against it.

## 5. Ship as a pre-commit hook and GitHub Action

The scanner has no runtime dependencies and imports nothing, which makes it unusually easy
to drop into CI. A `--fail-under` threshold would let a project ratchet down over time.

## 6. Scan a random sample of PyPI, not a sample of convenience

161 packages - whatever happened to be installed locally - show the phenomenon exists at
roughly **1.93%**. A random sample of the top 1,000 PyPI packages would say whether that
rate is typical, and whether drift correlates with project size, age or release cadence.

## 7. Correlate drift with commit history

Given a repository rather than installed source, `git log` can date the parameter rename
and the docstring's last edit - which answers **how long a docstring stays wrong**. That
is a more interesting number than the count.
