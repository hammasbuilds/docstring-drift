"""Find docstrings that disagree with the function they describe.

A docstring goes stale silently. Rename a parameter, add one, drop one - nothing
fails, no test breaks, and the documentation quietly starts lying. This finds those
cases by comparing what a docstring *claims* the parameters are against what the
signature actually says.

Pure AST analysis: no imports, no execution, no network, no model. That means it runs
safely over third-party code you did not write, and the result is deterministic.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

# Google style:  "Args:\n    name (int): description"
# NumPy style:   "Parameters\n----------\nname : int"
# Sphinx style:  ":param name: description"
SPHINX = re.compile(r"^\s*:param\s+(?:[\w\[\], .]+\s+)?(\*{0,2}\w+)\s*:", re.MULTILINE)
SECTION = re.compile(
    r"^[ \t]*(Args|Arguments|Parameters|Params|Keyword Args|Keyword Arguments)\s*:?\s*$",
    re.MULTILINE | re.IGNORECASE,
)
NUMPY_RULE = re.compile(r"^[ \t]*-{3,}[ \t]*$")
ENTRY = re.compile(r"^[ \t]*(\*{0,2}[A-Za-z_]\w*)[ \t]*(?:\([^)]*\))?[ \t]*:")
NUMPY_ENTRY = re.compile(r"^[ \t]*(\*{0,2}[A-Za-z_]\w*)[ \t]*(?::[ \t]*.*)?$")

# Sections that end an argument block.
#
# Two things here were wrong and both inflated the headline.
#
# The pattern ended in `\s*$`, so it only matched a header sitting alone on its
# line. Real docstrings write `Returns: the loss value`, which fell through to
# ENTRY and was recorded as a parameter named `Returns` — 84 times in six
# packages, the single most "documented" parameter in the corpus.
#
# And the list was short. `Definitions`, `Requirements`, `Relations`, `Shape`,
# `Inputs`, `Outputs` and singular `Warning` are all common headers that were
# missing, so everything beneath them was read as parameters.
STOP = re.compile(
    r"^[ \t]*(Returns?|Yields?|Raises?|Examples?|Notes?|See Also|See|References?|"
    r"Attributes?|Warns|Warnings?|Todo|Shape|Inputs?|Outputs?|Requirements?|"
    r"Relations?|Definitions?|Usage|Methods?|Tip|Hint|Caution|Danger|Important|"
    r"Attention|Deprecated|Version|Added|Changed)\s*:?.*$",
    re.MULTILINE | re.IGNORECASE,
)

# A URL in a description is not a parameter. `https://example.com` matches
# ENTRY because `https` is a word followed by a colon, which put `https` in
# the results five times across six packages.
URLISH = re.compile(r"^\s*\*{0,2}(?:https?|ftp|ftps|file|mailto|ssh|git)\s*:", re.IGNORECASE)

SELFISH = {"self", "cls"}


def documented_params(docstring: str) -> set[str]:
    """Parameter names a docstring claims to document, across the three common styles."""
    if not docstring:
        return set()

    found = {m.group(1).lstrip("*") for m in SPHINX.finditer(docstring)}

    lines = docstring.splitlines()
    inside = False
    entry_indent: int | None = None
    for i, line in enumerate(lines):
        if SECTION.match(line):
            inside = True
            entry_indent = None
            continue
        if inside and STOP.match(line):
            inside = False
            continue
        if not inside or NUMPY_RULE.match(line) or not line.strip():
            continue
        if URLISH.match(line):
            continue

        indent = len(line) - len(line.lstrip())
        # Parameter names sit at one fixed indent; their descriptions are indented
        # further. Without this, prose like "Default: None" inside a description
        # parses as a parameter called `Default` - which is how this scanner first
        # "discovered" hundreds of phantom params across scipy that did not exist.
        if entry_indent is not None and indent > entry_indent:
            continue

        name = None
        match = ENTRY.match(line)  # google: "name (type): desc"
        if match:
            name = match.group(1)
        elif " : " in line:  # numpy: "name : type"
            numpy = NUMPY_ENTRY.match(line.split(" : ")[0])
            if numpy:
                name = numpy.group(1)
        elif (
            i + 1 < len(lines)
            and lines[i + 1].strip()
            and len(lines[i + 1]) - len(lines[i + 1].lstrip()) > indent
        ):  # numpy with no type, description indented beneath
            numpy = NUMPY_ENTRY.match(line)
            if numpy:
                name = numpy.group(1)

        if name:
            found.add(name.lstrip("*"))
            if entry_indent is None:
                entry_indent = indent

    # `self`/`cls` are stripped from signatures too, so documenting them must not
    # register as a phantom parameter.
    return {f for f in found if f and not f[0].isdigit() and f not in SELFISH}


def signature_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = node.args
    names = [p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    return [n for n in names if n not in SELFISH]


@dataclass
class Finding:
    file: str
    line: int
    function: str
    kind: str  # "phantom" | "undocumented"
    name: str

    def describe(self) -> str:
        if self.kind == "phantom":
            return (
                f"docstring documents `{self.name}`, which is not a parameter of `{self.function}`"
            )
        return f"`{self.name}` is a parameter of `{self.function}` but is not documented"


def scan_source(source: str, filename: str) -> list[Finding]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            continue
        documented = documented_params(doc)
        if not documented:
            # A docstring with no parameter section is a choice, not a defect.
            continue
        actual = signature_params(node)

        # A function taking *args or **kwargs can legitimately document names that
        # never appear in its signature - numpy.einsum documents `dtype` and `casting`,
        # both passed through **kwargs. Reporting those as phantom is a false positive,
        # so only functions with a fully explicit signature are checked for them.
        catch_all = node.args.vararg is not None or node.args.kwarg is not None
        if not catch_all:
            for name in sorted(documented - set(actual)):
                findings.append(Finding(filename, node.lineno, node.name, "phantom", name))
        for name in actual:
            if name not in documented:
                findings.append(Finding(filename, node.lineno, node.name, "undocumented", name))
    return findings


def scan_path(root: Path, limit_files: int | None = None) -> tuple[list[Finding], dict]:
    files = sorted(p for p in root.rglob("*.py") if "test" not in p.parts)
    if limit_files:
        files = files[:limit_files]

    findings: list[Finding] = []
    functions = documented = 0
    for path in files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
                if ast.get_docstring(node) and documented_params(ast.get_docstring(node)):
                    documented += 1
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        findings.extend(scan_source(source, rel))

    stats = {
        "files": len(files),
        "functions": functions,
        "with_param_docs": documented,
        "phantom": sum(1 for f in findings if f.kind == "phantom"),
        "undocumented": sum(1 for f in findings if f.kind == "undocumented"),
    }
    return findings, stats


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    findings, stats = scan_path(target)
    print(f"scanned {stats['files']} files, {stats['functions']} functions")
    print(f"  with a documented parameter list: {stats['with_param_docs']}")
    print(f"  PHANTOM (documented, does not exist): {stats['phantom']}")
    print(f"  undocumented parameters            : {stats['undocumented']}")
    print("\nfirst phantom findings:")
    for f in [f for f in findings if f.kind == "phantom"][:12]:
        print(f"  {f.file}:{f.line}  {f.describe()}")
