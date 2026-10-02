import pytest

from app.workbook.formula import (
    FormulaError,
    evaluate,
    parse_formula,
    parse_cell_ref,
)


def _resolve_from(values: dict[tuple[int, int], float]):
    def resolver(row: int, col: int) -> float:
        return values.get((row, col), 0.0)
    return resolver


def _eval(src: str, values: dict | None = None) -> float:
    node = parse_formula(src)
    return evaluate(node, _resolve_from(values or {}))


def test_numbers():
    assert _eval("42") == 42.0
    assert _eval("3.5") == 3.5


def test_basic_arithmetic():
    assert _eval("1 + 2") == 3.0
    assert _eval("10 - 4") == 6.0
    assert _eval("3 * 4") == 12.0
    assert _eval("20 / 4") == 5.0


def test_operator_precedence():
    assert _eval("1 + 2 * 3") == 7.0
    assert _eval("(1 + 2) * 3") == 9.0


def test_unary_minus():
    assert _eval("-5") == -5.0
    assert _eval("-5 + 10") == 5.0


def test_percentage():
    assert _eval("50%") == 0.5
    assert _eval("100 * 20%") == 20.0


def test_cell_reference():
    assert _eval("A1", {(1, 1): 7.0}) == 7.0
    assert _eval("A1 + B1", {(1, 1): 3.0, (1, 2): 4.0}) == 7.0


def test_cell_reference_multi_letter():
    assert _eval("AA1", {(1, 27): 9.0}) == 9.0


def test_sum_range():
    assert _eval(
        "SUM(A1:A3)",
        {(1, 1): 1.0, (2, 1): 2.0, (3, 1): 3.0},
    ) == 6.0


def test_min_max():
    vals = {(1, 1): 5.0, (2, 1): 2.0, (3, 1): 8.0}
    assert _eval("MIN(A1:A3)", vals) == 2.0
    assert _eval("MAX(A1:A3)", vals) == 8.0


def test_round():
    assert _eval("ROUND(3.14159, 2)") == 3.14
    assert _eval("ROUND(2.5, 0)") == 3.0  # banker's? No: HALF_UP → 3


def test_division_by_zero():
    with pytest.raises(FormulaError):
        _eval("1 / 0")


def test_unknown_function_rejected():
    with pytest.raises(FormulaError):
        _eval("EVIL(1, 2)")


def test_unbalanced_parens():
    with pytest.raises(FormulaError):
        _eval("(1 + 2")


def test_invalid_token():
    with pytest.raises(FormulaError):
        _eval("1 @ 2")


def test_parse_cell_ref():
    r = parse_cell_ref("B3")
    assert r.row == 3
    assert r.col == 2


def test_no_eval_injection():
    """Any attempt to sneak in Python-like expressions fails cleanly."""
    with pytest.raises(FormulaError):
        _eval("__import__('os').system('ls')")