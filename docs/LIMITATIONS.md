# Limitations

[<- back to README](../README.md)

## Only parameter names

It does not check types, descriptions, return values, or whether a description is still
accurate. A docstring claiming `int` for a `str` parameter passes. Those need more than
AST comparison.

## Catch-all functions are exempt

Functions with `*args` or `**kwargs` are never reported for phantom parameters, so drift
in a kwargs-heavy API is invisible here.

**This is a deliberate precision-over-recall trade.** A false positive in a linter costs
far more than a miss: one wrong finding and a team turns the tool off. The exemption
removes an entire class of false positive at the cost of some recall.

[FUTURE.md](FUTURE.md) describes how that recall could be recovered.

## Exact-match, not similarity

A docstring documenting `filepath` when the parameter is `file_path` is reported as one
phantom plus one undocumented, rather than as a probable rename. The two findings sit
adjacent in the output, but the tool does not connect them.

## Results depend on installed versions

The scan reads installed source, so figures reflect whichever versions are present. A
different environment gives slightly different counts.

## Undocumented is a weak signal

The `undocumented` count is reported but deliberately excluded from the phantom rate.
Omitting a parameter from a docstring is frequently intentional - internal arguments,
deprecated ones, or ones covered in prose - so it cannot be treated as a defect the way a
phantom can.

## Not a random sample of the ecosystem

The 161 packages scanned are whatever happened to be installed across the venvs on the
machine that ran the scan - convenient, not random. That's enough to show the phenomenon
exists and to size it roughly among widely-used libraries, but not enough to claim the
measured rate is representative of PyPI generally. See [FUTURE.md](FUTURE.md) for what a
real random sample would take.
