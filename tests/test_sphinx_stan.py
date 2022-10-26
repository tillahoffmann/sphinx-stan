import pytest
from sphinxcontrib.stan import Signature, TypedIdentifier
from typing import Optional


# Test examples from https://mc-stan.org/docs/stan-users-guide/functions-programming.html.
@pytest.mark.parametrize("signature, expected, kwargs", [
    (
        "void basic()",
        Signature("basic", "void", args=[]),
        None,
    ),
    (
        "real relative_diff(real x, real y)",
        Signature("relative_diff", "real", args=[TypedIdentifier("x", "real"),
                                                 TypedIdentifier("y", "real")]),
        None,
    ),
    (
        "real dbl_sqrt(real x)",
        Signature("dbl_sqrt", "real", args=[TypedIdentifier("x", "real")]),
        None,
    ),
    (
        "real entropy(vector theta)",
        Signature("entropy", "real", args=[TypedIdentifier("theta", "vector")]),
        None,
    ),
    (
        "array [] real baz(array [,] real x)",
        Signature("baz", "real", 1, args=[TypedIdentifier("x", "real", 2)]),
        None,
    ),
    (
        "void overloaded(array [,,] real)",
        Signature("overloaded", "void", args=[TypedIdentifier(None, "real", 3)]),
        {"parse_arg_identifiers": False},
    ),
    (
        "overloaded(array [,] real)",
        Signature("overloaded", None, args=[TypedIdentifier(None, "real", 2)]),
        {"parse_arg_identifiers": False, "parse_type": False},
    )
])
def test_parse_signature(signature: str, expected: dict, kwargs: Optional[dict]) -> None:
    kwargs = kwargs or {}
    actual = Signature.parse(signature, **kwargs)
    assert actual == expected
    assert str(actual) == signature


@pytest.mark.parametrize("target, candidate, result", [
    ("overload", "void overload(real x, int y)", 1),
    ("overload(real, real)", "void overload(real x, int y)", 0),
    ("overload(real)", "void overload(real x, int y)", 0),
    ("overload(real, int)", "void overload(real x, int y)", 2),
    ("overload(real, int)", "void overload(real x, array [,] int y)", 0),
    ("overload(real, array [,,] int)", "void overload(real x, array [,] int y)", 0),
    ("overload(real, array [,] int)", "void overload(real x, array [,] int y)", 2),
    ("overloaded", "void overload(real x, int y)", 0),
    ("overloaded(real, int)", "void overload(real x, int y)", 0),
])
def test_match_signature(target: str, candidate: str, result: int) -> None:
    target = Signature.parse(target, parse_type=False, parse_arg_identifiers=False)
    candidate = Signature.parse(candidate)
    assert target.matches(candidate) == result
