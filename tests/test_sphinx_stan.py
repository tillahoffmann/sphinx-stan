import pytest
from sphinxcontrib.stan import parse_signature


# Test examples from https://mc-stan.org/docs/stan-users-guide/functions-programming.html.
@pytest.mark.parametrize("signature, expected, parse_arg_identifiers", [
    (
        "void basic()",
        {"type": "void", "identifier": "basic", "args": []},
        True,
    ),
    (
        "real relative_diff(real x, real y)",
        {"type": "real", "identifier": "relative_diff", "args": [
            {"type": "real", "identifier": "x"},
            {"type": "real", "identifier": "y"},
        ]},
        True,
    ),
    (
        "real dbl_sqrt(real x)",
        {"type": "real", "identifier": "dbl_sqrt", "args": [
            {"type": "real", "identifier": "x"},
        ]},
        True,
    ),
    (
        "real entropy(vector theta)",
        {"type": "real", "identifier": "entropy", "args": [
            {"type": "vector", "identifier": "theta"},
        ]},
        True,
    ),
    (
        "array[] real baz(array[,] real x)",
        {"type": ("real", 1), "identifier": "baz", "args": [
            {"type": ("real", 2), "identifier": "x"},
        ]},
        True,
    ),
    (
        "void overloaded(real)",
        {"type": "void", "identifier": "overloaded", "args": [{"type": "real"}]},
        False,
    )
])
def test_parse_signature(signature: str, expected: dict, parse_arg_identifiers: bool) -> None:
    actual, _ = parse_signature(signature, parse_arg_identifiers)
    assert actual == expected
