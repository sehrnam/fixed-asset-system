"""
Safe formula engine — approved subset only (Doc 03 §5, Doc 10).

Grammar (recursive descent):
    expression  := term (('+' | '-') term)*
    term        := factor (('*' | '/') factor)*
    factor      := primary ('%')?
    primary     := NUMBER
                 | CELLREF
                 | FUNCALL
                 | '(' expression ')'
                 | '-' primary
    funcall     := NAME '(' args ')'
    args        := arg (',' arg)*
    arg         := RANGE | expression
    RANGE       := CELLREF ':' CELLREF

Functions: SUM, MIN, MAX, ROUND
Ranges: only inside functions.
No eval/exec, no macros, no external links.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


class FormulaError(Exception):
    """Raised for any invalid formula, cycle, or unsupported construct."""


# ---------- tokenizer ----------

TOKEN_RE = re.compile(
    r"""
    (?P<WS>\s+)
  | (?P<NUMBER>\d+(\.\d+)?)
  | (?P<CELLREF>[A-Za-z]{1,3}\d{1,5})
  | (?P<NAME>[A-Za-z]+)
  | (?P<OP>[-+*/%(),:])
""",
    re.VERBOSE,
)


@dataclass
class Token:
    kind: str
    value: str


def tokenize(src: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise FormulaError(f"Unexpected character at position {pos}: {src[pos]!r}")
        kind = m.lastgroup
        value = m.group()
        pos = m.end()
        if kind == "WS":
            continue
        # NAME is only valid if it's immediately followed by '(' → function
        if kind == "NAME":
            # Look ahead for '('
            la = pos
            while la < len(src) and src[la].isspace():
                la += 1
            if la < len(src) and src[la] == "(":
                tokens.append(Token("FUNC", value.upper()))
            else:
                raise FormulaError(f"Unknown identifier: {value!r}")
            continue
        tokens.append(Token(kind, value))
    return tokens


# ---------- AST ----------

@dataclass
class Num:
    value: float


@dataclass
class Ref:
    row: int
    col: int


@dataclass
class RangeRef:
    start: Ref
    end: Ref


@dataclass
class BinOp:
    op: str
    left: object
    right: object


@dataclass
class UnaryMinus:
    operand: object


@dataclass
class Percent:
    operand: object


@dataclass
class Func:
    name: str
    args: list


# ---------- parser ----------

CELL_REF_RE = re.compile(r"^([A-Za-z]{1,3})(\d{1,5})$")


def parse_cell_ref(text: str) -> Ref:
    m = CELL_REF_RE.match(text)
    if not m:
        raise FormulaError(f"Invalid cell reference: {text!r}")
    letters, digits = m.group(1).upper(), m.group(2)
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    row = int(digits)
    return Ref(row=row, col=col)


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> Token:
        tok = self.peek()
        if tok is None:
            raise FormulaError("Unexpected end of formula")
        self.pos += 1
        return tok

    def expect(self, kind: str, value: str | None = None) -> Token:
        tok = self.next()
        if tok.kind != kind or (value is not None and tok.value != value):
            raise FormulaError(f"Expected {value or kind}, got {tok.value!r}")
        return tok

    def parse(self):
        node = self.parse_expression()
        if self.peek() is not None:
            raise FormulaError(f"Unexpected trailing token: {self.peek().value!r}")
        return node

    def parse_expression(self):
        node = self.parse_term()
        while True:
            tok = self.peek()
            if tok and tok.kind == "OP" and tok.value in ("+", "-"):
                self.next()
                right = self.parse_term()
                node = BinOp(op=tok.value, left=node, right=right)
            else:
                return node

    def parse_term(self):
        node = self.parse_factor()
        while True:
            tok = self.peek()
            if tok and tok.kind == "OP" and tok.value in ("*", "/"):
                self.next()
                right = self.parse_factor()
                node = BinOp(op=tok.value, left=node, right=right)
            else:
                return node

    def parse_factor(self):
        node = self.parse_primary()
        while True:
            tok = self.peek()
            if tok and tok.kind == "OP" and tok.value == "%":
                self.next()
                node = Percent(operand=node)
            else:
                return node

    def parse_primary(self):
        tok = self.next()

        if tok.kind == "NUMBER":
            return Num(value=float(tok.value))

        if tok.kind == "CELLREF":
            ref = parse_cell_ref(tok.value)
            # Check for range in function-args context
            return ref

        if tok.kind == "FUNC":
            return self.parse_function(tok.value)

        if tok.kind == "OP" and tok.value == "(":
            node = self.parse_expression()
            self.expect("OP", ")")
            return node

        if tok.kind == "OP" and tok.value == "-":
            return UnaryMinus(operand=self.parse_primary())

        raise FormulaError(f"Unexpected token: {tok.value!r}")

    def parse_function(self, name: str):
        self.expect("OP", "(")
        args: list = []
        if self.peek() and self.peek().kind == "OP" and self.peek().value == ")":
            self.next()
        else:
            args.append(self.parse_arg())
            while self.peek() and self.peek().kind == "OP" and self.peek().value == ",":
                self.next()
                args.append(self.parse_arg())
            self.expect("OP", ")")
        return Func(name=name, args=args)

    def parse_arg(self):
        # Detect a range: CELLREF ':' CELLREF
        tok = self.peek()
        if tok and tok.kind == "CELLREF":
            # Peek two ahead
            if (
                self.pos + 1 < len(self.tokens)
                and self.tokens[self.pos + 1].kind == "OP"
                and self.tokens[self.pos + 1].value == ":"
            ):
                start_tok = self.next()
                self.expect("OP", ":")
                end_tok = self.next()
                if end_tok.kind != "CELLREF":
                    raise FormulaError("Range must end with a cell reference")
                return RangeRef(
                    start=parse_cell_ref(start_tok.value),
                    end=parse_cell_ref(end_tok.value),
                )
        return self.parse_expression()


def parse_formula(src: str):
    """Parse a formula WITHOUT the leading '='."""
    tokens = tokenize(src)
    return Parser(tokens).parse()


# ---------- evaluator ----------

CellResolver = Callable[[int, int], float]  # (row, col) -> numeric value


def _iter_range(rng: RangeRef):
    r1, r2 = rng.start.row, rng.end.row
    c1, c2 = rng.start.col, rng.end.col
    if r1 > r2:
        r1, r2 = r2, r1
    if c1 > c2:
        c1, c2 = c2, c1
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            yield r, c


def evaluate(node, resolve: CellResolver) -> float:
    """Evaluate the AST. `resolve(row, col)` returns the numeric value of a cell.

    Raises FormulaError for unsupported constructs or non-numeric operands.
    """
    if isinstance(node, Num):
        return float(node.value)

    if isinstance(node, Ref):
        return float(resolve(node.row, node.col))

    if isinstance(node, UnaryMinus):
        return -evaluate(node.operand, resolve)

    if isinstance(node, Percent):
        return evaluate(node.operand, resolve) / 100.0

    if isinstance(node, BinOp):
        left = evaluate(node.left, resolve)
        right = evaluate(node.right, resolve)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise FormulaError("Division by zero")
            return left / right
        raise FormulaError(f"Unsupported operator: {node.op}")

    if isinstance(node, Func):
        return _eval_func(node, resolve)

    raise FormulaError(f"Unsupported AST node: {type(node).__name__}")


def _eval_func(node: Func, resolve: CellResolver) -> float:
    name = node.name.upper()

    if name in ("SUM", "MIN", "MAX"):
        values = _flatten_args(node.args, resolve)
        if not values:
            return 0.0
        if name == "SUM":
            return float(sum(values))
        if name == "MIN":
            return float(min(values))
        return float(max(values))

    if name == "ROUND":
        if len(node.args) != 2:
            raise FormulaError("ROUND takes exactly 2 arguments")
        value = _arg_to_number(node.args[0], resolve)
        places = int(_arg_to_number(node.args[1], resolve))
        if places < 0 or places > 8:
            raise FormulaError("ROUND places must be between 0 and 8")
        from decimal import Decimal, ROUND_HALF_UP
        quant = Decimal("1").scaleb(-places)
        return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))

    raise FormulaError(f"Unsupported function: {name}")


def _arg_to_number(arg, resolve: CellResolver) -> float:
    if isinstance(arg, RangeRef):
        values = [resolve(r, c) for r, c in _iter_range(arg)]
        if len(values) != 1:
            raise FormulaError("Range used where a single value is required")
        return float(values[0])
    return evaluate(arg, resolve)


def _flatten_args(args: list, resolve: CellResolver) -> list[float]:
    out: list[float] = []
    for arg in args:
        if isinstance(arg, RangeRef):
            for r, c in _iter_range(arg):
                out.append(float(resolve(r, c)))
        else:
            out.append(evaluate(arg, resolve))
    return out