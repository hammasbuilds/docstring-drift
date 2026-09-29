# Problems hit while building this

[<- back to README](../README.md)

**The first version reported roughly 400 phantom parameters in scipy alone, and almost
none were real.** Finding and removing those was most of the work on this project.

## 1. Prose parsed as parameters

`Default: None` inside a description matched the name pattern and became a parameter
called `Default`. So did `Note:`, `Example:`, and any sentence starting with a capitalised
word followed by a colon.

**This alone caused most of the scipy noise.**

**Fix:** track the indent of the first entry in a section. Parameter names sit at one
indent; descriptions are indented further, so anything deeper is skipped.

**Test:** `test_prose_in_a_description_is_not_a_parameter`

## 2. Catch-all signatures

`numpy.einsum` documents `dtype` and `casting`. Neither appears in its signature - both
are passed through `**kwargs`. The scanner reported both as phantom. So did
`pandas.set_option`, which takes `*args`.

**Fix:** functions taking `*args` or `**kwargs` are exempt from phantom reporting.

**Tests:** `test_kwargs_function_does_not_report_phantoms`,
`test_vararg_function_does_not_report_phantoms`

## 3. self / cls asymmetry

`self` and `cls` were stripped from signatures but not from docstrings, so any docstring
documenting `cls` produced a phantom.

**Fix:** ignored on both sides.

**Test:** `test_self_and_cls_are_never_parameters`

## 4. Trusting the first run

The initial numbers looked plausible and publishable. They were wrong.

What caught it was reading the *output* rather than the total: `Default` is not a credible
parameter name, and seeing it repeatedly was the signal that the parser - not scipy - was
at fault.

**Fix in process, not code:** a finding was verified by hand against real source before any
number was written down. That is how the pandas `round_trip_pickle` case was confirmed.

## The effect of the fixes

| Package | before | after |
|---|---:|---:|
| scipy | 434 | **27** |
| pandas | 106 | **40** |
| numpy | 55 | **8** |

The numbers in this repository are the post-fix ones.

## 5. The CLI itself did the thing it exists to catch

An independent review pointed the CLI at a mistyped path, a single file, and `--help`, and
got `scanned 0 files, 0 functions`, exit `0`, on all three - "clean," silently, when
nothing had actually been scanned. And the exit code was always `0`, even with findings,
so the README's "it works as a CI check" was not true: nothing could gate a build.

Root cause: `sys.argv[1]` was read directly with no validation, and `Path(root).rglob(...)`
on a nonexistent path or a single file both yield an empty iterator with no error - the
scanner reported success because it never noticed it hadn't scanned anything. For a tool
whose whole premise is "nothing fails, nothing complains, the truth just quietly stops
being true," that's the same failure class turned on itself.

**Fix:** `scan_path` now raises `FileNotFoundError` on a path that doesn't exist and
accepts a single file directly instead of silently globbing nothing; `src/drift.py` gained
a real `argparse` CLI (so `--help` is `--help`, not a path) and exits `1` on any phantom
finding, `2` on a bad path, `0` when clean.

**Tests:** `test_scan_path_raises_on_a_nonexistent_path`,
`test_scan_path_accepts_a_single_file`, `test_main_exits_nonzero_on_a_nonexistent_path`,
`test_main_exits_nonzero_when_it_finds_phantom_parameters`,
`test_main_exits_zero_when_clean`, `test_main_help_does_not_get_parsed_as_a_path`.
