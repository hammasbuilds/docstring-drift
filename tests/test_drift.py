"""Tests for the docstring/signature comparison.

Several of these exist because the scanner's first run produced hundreds of findings
that were not real. Each false-positive class it used to emit now has a test, so the
noise cannot come back silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ast

from drift import documented_params, main, scan_path, scan_source, signature_params


def params_of(src: str) -> list[str]:
    node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
    return signature_params(node)


# --- docstring parsing ------------------------------------------------------------------


def test_google_style():
    doc = "Summary.\n\nArgs:\n    alpha (int): first\n    beta (str): second\n"
    assert documented_params(doc) == {"alpha", "beta"}


def test_numpy_style():
    doc = "Summary.\n\nParameters\n----------\nalpha : int\n    first\nbeta : str\n    second\n"
    assert documented_params(doc) == {"alpha", "beta"}


def test_sphinx_style():
    doc = "Summary.\n\n:param alpha: first\n:param int beta: second\n"
    assert documented_params(doc) == {"alpha", "beta"}


def test_stops_at_returns_section():
    doc = "Args:\n    alpha (int): first\n\nReturns:\n    total (int): the sum\n"
    assert documented_params(doc) == {"alpha"}


def test_no_parameter_section_documents_nothing():
    assert documented_params("Just a summary line.") == set()


def test_empty_docstring():
    assert documented_params("") == set()
    assert documented_params(None) == set()


def test_stars_are_stripped():
    doc = "Args:\n    *args: positional\n    **kwargs: keyword\n"
    assert documented_params(doc) == {"args", "kwargs"}


# --- regression: false positives the first version produced -------------------------------


def test_prose_in_a_description_is_not_a_parameter():
    """Regression: "Default: None" inside a description parsed as a param `Default`.

    This alone accounted for most of the ~400 phantom findings the first scan reported
    across scipy. Names sit at one indent; descriptions are indented further.
    """
    doc = (
        "Parameters\n----------\nalpha : int\n"
        "    The value.\n    Default: None\n    Note: see below\n"
    )
    assert documented_params(doc) == {"alpha"}


def test_self_and_cls_are_never_parameters():
    """Regression: documenting `cls` was reported as phantom, because signatures
    strip self/cls but docstring parsing did not."""
    doc = "Args:\n    cls: the class\n    alpha (int): real\n"
    assert documented_params(doc) == {"alpha"}


def test_kwargs_function_does_not_report_phantoms():
    """Regression: numpy.einsum documents `dtype` and `casting`, both passed through
    **kwargs. A catch-all signature can legitimately document anything."""
    src = (
        "def f(*operands, **kwargs):\n"
        '    """Do a thing.\n\n    Args:\n        dtype (type): out type\n'
        '        casting (str): rule\n    """\n'
    )
    assert [f for f in scan_source(src, "x.py") if f.kind == "phantom"] == []


def test_vararg_function_does_not_report_phantoms():
    src = 'def f(*args):\n    """S.\n\n    Args:\n        pattern (str): p\n    """\n'
    assert [f for f in scan_source(src, "x.py") if f.kind == "phantom"] == []


# --- signatures ---------------------------------------------------------------------------


def test_signature_drops_self():
    assert params_of("class C:\n    def m(self, a, b):\n        pass\n") == ["a", "b"]


def test_signature_includes_kwonly_and_varargs():
    got = params_of("def f(a, *rest, key=1, **extra):\n    pass\n")
    assert got == ["a", "key", "rest", "extra"]


# --- end to end ----------------------------------------------------------------------------


def test_detects_a_renamed_parameter():
    """The real pandas case: the parameter became `tmp_path`, the docstring still says
    `path`."""
    src = (
        "def round_trip_pickle(obj, tmp_path):\n"
        '    """Pickle and read back.\n\n    Parameters\n    ----------\n'
        "    obj : any\n        The object.\n    path : str\n        Where.\n"
        '    """\n'
    )
    findings = scan_source(src, "io.py")
    phantom = [f for f in findings if f.kind == "phantom"]
    assert [f.name for f in phantom] == ["path"]
    assert "tmp_path" in [f.name for f in findings if f.kind == "undocumented"]


def test_agreeing_docstring_produces_nothing():
    src = (
        "def f(alpha, beta):\n"
        '    """S.\n\n    Args:\n        alpha (int): a\n        beta (int): b\n    """\n'
    )
    assert scan_source(src, "x.py") == []


def test_syntax_error_is_skipped_not_raised():
    assert scan_source("def f(:\n", "broken.py") == []


def test_function_without_docstring_is_ignored():
    assert scan_source("def f(a, b):\n    return a\n", "x.py") == []


@pytest.mark.parametrize("style", ["google", "numpy", "sphinx"])
def test_all_styles_catch_the_same_drift(style):
    body = {
        "google": '    """S.\n\n    Args:\n        gone (int): x\n    """\n',
        "numpy": '    """S.\n\n    Parameters\n    ----------\n    gone : int\n        x\n    """\n',
        "sphinx": '    """S.\n\n    :param gone: x\n    """\n',
    }[style]
    findings = scan_source("def f(here):\n" + body, "x.py")
    assert [f.name for f in findings if f.kind == "phantom"] == ["gone"]


# --- section headers read as parameters -------------------------------------
#
# Found by scanning 161 installed packages instead of eight. The top six
# "documented parameters" in the corpus were all docstring section headers,
# and they were 53% of every finding: 679 phantom results became 321 once
# these were fixed. Each string below is copied from a real library.


def test_a_section_header_with_trailing_text_is_not_a_parameter():
    """The single biggest false positive: 84 occurrences of `Returns`.

    STOP only matched a header alone on its line, so "Returns: the loss"
    fell through to the entry pattern and was recorded as a parameter.
    """
    doc = """Build the loss.

    Args:
        labels: labels of the batch
        embeddings: tensor of shape (batch_size, embed_dim)

    Returns: scalar tensor containing the triplet loss
    """
    assert documented_params(doc) == {"labels", "embeddings"}


@pytest.mark.parametrize(
    "header",
    [
        "Returns",
        "Example",
        "Examples",
        "See Also",
        "Shape",
        "Inputs",
        "Outputs",
        "Requirements",
        "Relations",
        "Definitions",
        "Warning",
        "Warnings",
        "Notes",
        "References",
        "Usage",
        "Methods",
        "Tip",
        "Caution",
        "Deprecated",
    ],
)
def test_every_known_section_header_ends_the_argument_block(header):
    doc = f"""Summary.

    Args:
        real_one: a genuine parameter

    {header}:
        not_a_parameter: this is prose under a heading
    """
    assert documented_params(doc) == {"real_one"}


def test_a_url_in_a_description_is_not_a_parameter():
    """`https` was reported five times across six packages.

    A URL matches the entry pattern because `https` is a word followed by a
    colon.
    """
    doc = """Summary.

    Args:
        model: the model to use
        https://github.com/example/repo: not a parameter
    """
    assert "https" not in documented_params(doc)
    assert "model" in documented_params(doc)


def test_the_real_sentence_transformers_docstring_still_reports_its_drift():
    """The true positive this must not lose while removing false ones.

    `batch_all_triplet_loss(self, labels, embeddings)` documents `margin` and
    `squared`, and neither is a parameter. Verified against the installed
    source before this test was written.
    """
    doc = """Build the triplet loss over a batch of embeddings.

    Args:
        labels: labels of the batch, of size (batch_size,)
        embeddings: tensor of shape (batch_size, embed_dim)
        margin: margin for triplet loss
        squared: Boolean. If true, output is the pairwise squared distance.

    Returns:
        Label_Sentence_Triplet: scalar tensor containing the triplet loss
    """
    found = documented_params(doc)
    assert {"margin", "squared"} <= found
    assert "Returns" not in found
    assert "Label_Sentence_Triplet" not in found


# --- CLI / scan_path: a nonexistent path or a single file must not silently say "clean" ---
#
# Round 1 scoring found the CLI reports "scanned 0 files, 0 functions", exit 0, on a
# mistyped path, on a single .py file (rglob on a file yields nothing), and on --help
# (there was no argparse, so it was parsed as a path). And the exit code was always 0
# even with findings, so "it works as a CI check" (README) was not true. All four are
# regression-tested here.


def test_scan_path_raises_on_a_nonexistent_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_path(tmp_path / "does_not_exist_xyz")


def test_scan_path_accepts_a_single_file(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('def f(a):\n    """Args:\n        b: phantom\n    """\n', encoding="utf-8")
    findings, stats = scan_path(f)
    assert stats["files"] == 1
    assert stats["phantom"] == 1
    assert findings[0].file == "mod.py"  # not "." (relative_to itself)


def test_scan_path_excludes_tests_directory_not_just_test(tmp_path):
    """The original filter was `"test" not in p.parts`, which only excludes a
    directory literally named `test` (singular) - not `tests`, the far more common
    convention, and the one this project itself uses."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(
        'def f(a):\n    """Args:\n        b: phantom\n    """\n', encoding="utf-8"
    )
    findings, stats = scan_path(tmp_path)
    assert stats["files"] == 0
    assert findings == []


def test_main_exits_nonzero_on_a_nonexistent_path(tmp_path, capsys):
    code = main([str(tmp_path / "does_not_exist_xyz")])
    assert code == 2
    assert "does not exist" in capsys.readouterr().err


def test_main_exits_nonzero_when_it_finds_phantom_parameters(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('def f(a):\n    """Args:\n        b: phantom\n    """\n', encoding="utf-8")
    assert main([str(f)]) == 1


def test_main_exits_zero_when_clean(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('def f(a):\n    """Args:\n        a: real\n    """\n', encoding="utf-8")
    assert main([str(f)]) == 0


def test_main_help_does_not_get_parsed_as_a_path(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_main_json_output_is_valid_and_carries_the_finding(tmp_path, capsys):
    f = tmp_path / "mod.py"
    f.write_text('def f(a):\n    """Args:\n        b: phantom\n    """\n', encoding="utf-8")
    code = main([str(f), "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["stats"]["phantom"] == 1
    assert payload["findings"][0]["name"] == "b"
    assert payload["findings"][0]["kind"] == "phantom"


def test_main_json_output_on_a_bad_path_is_still_valid_json(tmp_path, capsys):
    code = main([str(tmp_path / "nope"), "--json"])
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload
