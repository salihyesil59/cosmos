"""Checking numeric answers to the worked problems (G15). GUI independent.

A learner types a number the way people write numbers: ``4.25``, ``4,25``,
``5.6e11``, ``5.6×10^11``, ``5.6 x 10¹¹``, ``−0.53``. :func:`parse_number` turns
that into a float and :func:`check_answer` compares it with the expected value,
recognising the two mistakes that are worth pointing out: a wrong power of ten
(usually a unit conversion) and a wrong sign.
"""

from __future__ import annotations

import enum
import math
import re
from dataclasses import dataclass

_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_POWER = re.compile(r"^(?P<mantissa>[-+]?\d*\.?\d+)\s*(?:[x×*·]\s*10\s*\^?\s*(?P<exponent>[-+]?\d+))$")


class Verdict(enum.Enum):
    CORRECT = "correct"
    CLOSE = "close"                   # within three tolerances: rounding or an intermediate value
    POWER_OF_TEN = "power_of_ten"     # right digits, wrong power of ten
    SIGN = "sign"                     # right size, wrong sign
    WRONG = "wrong"
    INVALID = "invalid"               # not a number


@dataclass(frozen=True)
class Result:
    verdict: Verdict
    value: float | None = None
    factor: int = 0                   # the power of ten the answer is off by, for POWER_OF_TEN

    @property
    def correct(self) -> bool:
        return self.verdict is Verdict.CORRECT


def parse_candidates(text: str) -> list[float]:
    """Every reasonable reading of what a person typed.

    A comma is ambiguous: ``4,246`` is 4.246 in Turkish or German and 4246 in English.
    Both readings are returned, the English one first when it is plausible.
    """
    s = text.strip().translate(_SUPERSCRIPTS)
    s = s.replace("−", "-").replace("–", "-").replace("\u2009", "").replace(" ", "")
    if not s:
        return []
    if "," in s and "." not in s:
        readings = [s.replace(",", "")] if re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+([x×*·].*)?", s) else []
        if s.count(",") == 1:
            readings.append(s.replace(",", "."))
    else:
        readings = [s.replace(",", "")]
    values = []
    for reading in readings:
        value = _to_float(reading)
        if value is not None and value not in values:
            values.append(value)
    return values


def _to_float(s: str) -> float | None:
    match = _POWER.match(s)
    if match:
        return float(match.group("mantissa")) * 10 ** int(match.group("exponent"))
    try:
        value = float(s)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_number(text: str) -> float | None:
    """The most likely number in what a person typed, or None."""
    values = parse_candidates(text)
    return values[0] if values else None


_RANK = ["correct", "sign", "power_of_ten", "close", "wrong"]


def check_answer(text: str, expected: float, tolerance: float = 0.02) -> Result:
    results = [_check_value(value, expected, tolerance) for value in parse_candidates(text)]
    if not results:
        return Result(Verdict.INVALID)
    return min(results, key=lambda r: _RANK.index(r.verdict.value))


def _check_value(value: float, expected: float, tolerance: float) -> Result:
    scale = abs(expected) if expected else 1.0
    miss = abs(value - expected)
    if miss <= tolerance * scale:
        return Result(Verdict.CORRECT, value)
    opposite = expected and value and math.copysign(1, value) != math.copysign(1, expected)
    if opposite and abs(abs(value) - abs(expected)) <= tolerance * scale:
        return Result(Verdict.SIGN, value)
    if expected and value and math.copysign(1, value) == math.copysign(1, expected):
        factor = round(math.log10(abs(value) / abs(expected)))
        if factor != 0 and abs(value / 10**factor - expected) <= tolerance * scale:
            return Result(Verdict.POWER_OF_TEN, value, factor)
    if miss <= 3 * tolerance * scale:
        return Result(Verdict.CLOSE, value)
    return Result(Verdict.WRONG, value)


def format_answer(value: float) -> str:
    """The expected answer, written the way the solution quotes it."""
    if value == 0:
        return "0"
    if 1e-3 <= abs(value) < 1e5:
        return f"{value:.4g}"
    exponent = math.floor(math.log10(abs(value)))
    return f"{value / 10**exponent:.3g} × 10^{exponent}"
