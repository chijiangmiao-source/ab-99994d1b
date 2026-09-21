"""Exact arithmetic in Q(sqrt(2)).

An element a + b*sqrt(2) with a, b in Z is represented as the pair (a, b).
The centrifuge only ever produces integer coefficients (masses are positive
integers and 2*cos/sin of k*pi/4 are in {0, +-1, +-2, +-sqrt(2)}), so no
floating point arithmetic is used anywhere.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Tuple

Pair = Tuple[int, int]
SQRT2_DISPLAY = "√2"  # √2


def zero() -> Pair:
    return (0, 0)


def add(x: Pair, y: Pair) -> Pair:
    return (x[0] + y[0], x[1] + y[1])


def sub(x: Pair, y: Pair) -> Pair:
    return (x[0] - y[0], x[1] - y[1])


def neg(x: Pair) -> Pair:
    return (-x[0], -x[1])


def mul(x: Pair, y: Pair) -> Pair:
    a, b = x
    c, d = y
    # (a + b√2)(c + d√2) = (ac + 2bd) + (ad + bc)√2
    return (a * c + 2 * b * d, a * d + b * c)


def scale(x: Pair, k: int) -> Pair:
    return (x[0] * k, x[1] * k)


def sign(x: Pair) -> int:
    """Exact sign of a + b√2: -1, 0 or 1."""
    a, b = x
    if b == 0:
        return (a > 0) - (a < 0)
    if a == 0:
        return (b > 0) - (b < 0)
    if a > 0 and b > 0:
        return 1
    if a < 0 and b < 0:
        return -1
    # Opposite signs: compare a^2 against 2 b^2. Equality cannot occur for
    # nonzero integers (sqrt 2 is irrational), but handle it as exact zero.
    lhs = a * a
    rhs = 2 * b * b
    if lhs == rhs:
        return 0
    if a > 0:  # b < 0: sign of a - |b|√2
        return 1 if lhs > rhs else -1
    # a < 0, b > 0: sign of |b|√2 - |a|
    return 1 if rhs > lhs else -1


def less(x: Pair, y: Pair) -> bool:
    return sign(sub(x, y)) < 0


def equal(x: Pair, y: Pair) -> bool:
    return x == y


def describe(x: Pair, divisor: int = 1) -> dict:
    """Render x / divisor exactly as normalised fractions of 1 and √2."""
    a, b = x
    fa = Fraction(a, divisor)
    fb = Fraction(b, divisor)
    return {
        "a_num": fa.numerator,
        "a_den": fa.denominator,
        "b_num": fb.numerator,
        "b_den": fb.denominator,
        "exact": _format(fa, fb),
    }


def _format(fa: Fraction, fb: Fraction) -> str:
    """Format fa + fb*√2 as a human readable exact string."""

    def rat(f: Fraction) -> str:
        return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"

    def term(f: Fraction, first: bool) -> str:
        if f == 0:
            return ""
        if f == 1:
            return SQRT2_DISPLAY
        if f == -1:
            return f"-{SQRT2_DISPLAY}"
        return f"{rat(f)}{SQRT2_DISPLAY}"

    parts: list[str] = []
    if fa != 0:
        parts.append(rat(fa))
    if fb != 0:
        t = term(fb, not parts)
        if parts and fb > 0:
            parts.append("+")
        parts.append(t)
    if not parts:
        return "0"
    return "".join(parts)
