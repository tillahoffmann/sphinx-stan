import pytest
from sphinxcontrib.stan import parse_signature


# Test examples from https://mc-stan.org/docs/stan-users-guide/functions-programming.html.
@pytest.mark.parametrize("signature, expected", [
    (
        "void basic()",
        {"type": "void", "identifier": "basic", "args": []},
    ),
    (
        "real relative_diff(real x, real y)",
        {"type": "real", "identifier": "relative_diff", "args": [
            {"type": "real", "identifier": "x"},
            {"type": "real", "identifier": "y"},
        ]},
    ),
    (
        "real dbl_sqrt(real x)",
        {"type": "real", "identifier": "dbl_sqrt", "args": [
            {"type": "real", "identifier": "x"},
        ]},
    ),
    (
        "real entropy(vector theta)",
        {"type": "real", "identifier": "entropy", "args": [
            {"type": "vector", "identifier": "theta"},
        ]},
    ),
    (
        "array[] real baz(array[,] real x)",
        {"type": ("real", 1), "identifier": "baz", "args": [
            {"type": ("real", 2), "identifier": "x"},
        ]},
    ),
])
def test_parse_signature(signature: str, expected: dict) -> None:
    actual, _ = parse_signature(signature)
    assert actual == expected
