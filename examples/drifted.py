"""Four functions whose docstrings describe parameters they do not have.

This file exists so `python demo.py` always demonstrates the tool, even on a
machine with nothing else installed. Each case is a shape taken from a real
library, not an invented one:

  renamed        a parameter was renamed and the docstring was not updated
  removed        a parameter was deleted and its documentation left behind
  never_existed  a docstring copied from a similar function
  numpy_style    the same failure in NumPy rather than Google format

`clean` is here as the control: a correct docstring that must not be reported.
"""

from __future__ import annotations


def renamed(labels, embeddings):
    """Build the triplet loss over a batch.

    Args:
        labels: labels of the batch
        embeddings: tensor of shape (batch_size, embed_dim)
        margin: margin for the triplet loss

    Returns: a scalar tensor
    """
    return labels, embeddings


def removed(path, encoding="utf-8"):
    """Read a file.

    Args:
        path: the file to read
        encoding: how to decode it
        errors: what to do with undecodable bytes
    """
    return path, encoding


def never_existed(model):
    """Score a model.

    Args:
        model: the model to score
        tokenizer: the tokenizer to use
        device: where to run
    """
    return model


def numpy_style(a, b):
    """Add two things.

    Parameters
    ----------
    a : int
        the first
    b : int
        the second
    out : ndarray
        where to write the result

    Returns
    -------
    int
    """
    return a + b


def clean(first, second=None):
    """A correct docstring, which must never be reported.

    Args:
        first: the first argument
        second: the optional second

    Returns:
        A tuple of both.
    """
    return first, second
