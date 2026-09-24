"""Worked problem sets (G15): content, answers recomputed from the engine, and answer checking."""

import math
import re

import pytest

from cosmos.content.loader import load_curriculum, load_problems
from cosmos.physics import constants as const
from cosmos.physics.presets import PRESETS
from cosmos.problems import Verdict, check_answer, format_answer, parse_candidates, parse_number

CURRICULUM = load_curriculum()
SETS = load_problems()
PROBLEMS = {p.id: p for s in SETS for p in s.problems}
PLANCK = PRESETS["planck18"].cosmology
G, C, MSUN, KPC, GPC, GYR = const.G, const.C, const.M_SUN, const.KPC, const.GPC, const.GYR


def _critical_density(h0: float) -> float:
    return 3 * (h0 * const.KM_S_MPC_TO_SI) ** 2 / (8 * math.pi * G)


# Every stored answer, computed independently from the statement and the physics engine.
EXPECTED = {
    "p0-proxima": 1 / 0.76807 * const.PARSEC / const.LIGHT_YEAR,
    "p0-sunlight": const.AU / C / 60,
    "p0-halpha": (721.93 / 656.28 - 1) * C / 1e3,
    "p0-andromeda": 2.54e6 * const.LIGHT_YEAR / const.MPC,
    "p0-galaxy-mass": (230e3) ** 2 * 8.2 * KPC / G / MSUN,
    "p1-hubble-law": 70 * 150,
    "p1-hubble-time": 1 / (70 * const.KM_S_MPC_TO_SI) / GYR,
    "p1-cepheid": 10 ** ((24.5 + 4.0 + 5) / 5) / 1e6,
    "p1-supernova": 10 ** ((16.2 + 19.3 + 5) / 5) / 1e6,
    "p1-cmb-peak": 2.8978e-3 / const.T_CMB * 1e3,
    "p2-scale-factor": 100 / (1 + 6),
    "p2-critical-density": _critical_density(67.66) / const.M_PROTON,
    "p2-hubble-radius": C / 1e3 / 67.66 / 1e3,
    "p2-luminosity-distance": float(PLANCK.luminosity_distance(1.0)) / 1e3,
    "p2-angular-size": 30 / (float(PLANCK.angular_diameter_distance(1.0)) * 1e3) * 206264.8,
    "p3-equality": 0.3097 / 9.14e-5 - 1,
    "p3-dark-energy-takes-over": (0.69 / 0.31) ** (1 / 3) - 1,
    "p3-deceleration": 0.31 / 2 - 0.69,
    "p3-eds-age": 2 / 3 / (67.66 * const.KM_S_MPC_TO_SI) / GYR,
    "p3-halo-mass": (220e3) ** 2 * 50 * KPC / G / MSUN,
    "p4-cmb-temperature": const.T_CMB * 1090,
    "p4-helium": 2 * (1 / 7) / (1 + 1 / 7),
    "p4-neutrino-temperature": (4 / 11) ** (1 / 3) * const.T_CMB,
    "p4-photons": 2 * 1.2020569 / math.pi**2 * (const.K_B * const.T_CMB / (const.HBAR * C)) ** 3 / 1e6,
    "p4-neutrino-density": 0.06 / 93.14 / 0.674**2,
    "p5-acoustic-scale": math.pi / 0.010411,
    "p5-bao-angle": math.degrees(147.1 / float(PLANCK.transverse_comoving_distance(0.5))),
    "p5-growth": 1e-3 * 1090 / 10,
    "p5-einstein-radius": math.sqrt(4 * G * 1e12 * MSUN / C**2 / (2 * GPC)) * 206264.8,
    "p5-collapse-time": math.sqrt(3 * math.pi / (32 * G * 200 * _critical_density(67.66))) / GYR,
    "p6-schwarzschild": 2 * G * MSUN / C**2 / 1e3,
    "p6-efolds": math.log(1e26),
    "p6-phi-squared": 8 / 60,
    "p6-siren": 3017 / 43.8,
    "p6-tension": (73.04 - 67.4) / math.hypot(1.04, 0.5),
    "p7-chi2-dof": 1540 / (1590 - 3),
    "p7-three-sigma": 3**2,
    "p7-neff": 20000 * 0.8 / 80,
    "p7-quadrature": math.sqrt(1.3**2 + 1.0**2 + 0.5**2),
    "p7-derived-error": math.sqrt(0.068**2 / 4 + 0.095**2 - 0.88 * 0.068 * 0.095),
    "p7-effective-volume": 10 * (1 / (1 + 1)) ** 2,
    "p7-systematic-floor": math.hypot(0.4, 0.3),
    "p7-effective-volume-mock": 2 / 0.02**2 + 1,
    "p7-redshift-space": 600 / 100,
    "p0-year-seconds": 365 * 24 * 3600,
    "p0-hubble-time": 1 / (70 * const.KM_S_MPC_TO_SI) / GYR,
    "p5-optical-depth": math.exp(-2 * 0.056),
    "p5-inflation-scale": 1.0e16 * (0.01 / 0.01) ** 0.25,
    "p6-m87-horizon": 2 * G * 6.5e9 * MSUN / C**2 / const.AU,
    "p6-hawking": const.HBAR * C**3 / (8 * math.pi * G * 10 * MSUN * const.K_B),
    "p6-horizon-mass": 1.0 / 1e5,
    # G25: problems for the Phase 4 lessons and simulators.
    "p3-recoil": 2 * (100 * 122.3 / 222.3) ** 2 * (220e3 / C) ** 2 / 122.3 * 1e6,
    "p3-axion-frequency": 4e-6 * const.EV / const.H_PLANCK / 1e6,
    "p3-exposure": 4.2 * 3e-48 / 1e-48,
    "p4-binding-temperature": 13.6 * const.EV / const.K_B,
    "p4-gas-temperature": const.T_CMB * 151 * (21 / 151) ** 2,
    "p4-21cm-frequency": 1420.405751 / 18,
    "p4-virial-temperature": 2e4 * 10 ** (2 / 3) * (1 + 9) / 10,
    "p5-disc-size": 0.035 * 230 / math.sqrt(2),
    "p5-peak-height": 1.686 / (0.6 * 0.61),
    "p5-baryons-in-stars": 0.035 / (0.0490 / 0.3097) * 100,
    "p6-big-rip": 2 / (3 * 0.5 * 70 * const.KM_S_MPC_TO_SI * math.sqrt(0.7)) / GYR,
    "p6-solar-system-rip": 365.25 * math.sqrt(2 * 3.5) / (6 * math.pi * 0.5),
    "p6-evaporation": 2.1e67 * 10**3,
    "p6-efold-time": 1 / (67.66 * const.KM_S_MPC_TO_SI * math.sqrt(0.69)) / GYR,
    "p7-s8": 0.811 * math.sqrt(0.315 / 0.3),
}


def test_one_set_per_level():
    assert [s.level for s in SETS] == [lv.number for lv in CURRICULUM.levels]
    for problem_set in SETS:
        assert problem_set.title and problem_set.intro
        assert len(problem_set.problems) >= 5, f"level {problem_set.level} needs at least five problems"


def test_problem_ids_are_unique():
    """Progress is stored by id, so two problems sharing one would share a result."""
    ids = [p.id for s in SETS for p in s.problems]
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_every_answer_is_recomputed():
    assert set(EXPECTED) == set(PROBLEMS)
    for pid, value in EXPECTED.items():
        problem = PROBLEMS[pid]
        assert problem.answer == pytest.approx(value, rel=min(problem.tolerance / 4, 2e-3)), pid
        # The stored answer must itself pass its own check.
        assert check_answer(format_answer(problem.answer), problem.answer, problem.tolerance).correct, pid


@pytest.mark.parametrize("pid", sorted(PROBLEMS))
def test_problem_is_well_formed(pid):
    problem = PROBLEMS[pid]
    lesson = CURRICULUM.lessons.get(problem.lesson)
    assert lesson is not None, f"{pid}: unknown lesson {problem.lesson}"
    assert lesson.level <= problem.level, f"{pid}: the lesson comes from a later level"
    assert problem.statement and problem.solution and len(problem.hints) >= 2
    assert 0 < problem.tolerance <= 0.05 and problem.difficulty in (1, 2, 3)
    if problem.simulator:
        from cosmos.gui.simulators.registry import SIMULATORS

        assert problem.simulator in SIMULATORS


def test_solutions_render():
    from cosmos.gui.rendering import math as mathrender
    from cosmos.gui.rendering.lesson_html import _DISPLAY_MATH, _INLINE_MATH

    for problem in PROBLEMS.values():
        text = problem.solution + " " + problem.statement
        formulas = [m.group(1) for m in _DISPLAY_MATH.finditer(text)]
        formulas += [m.group(1) for m in _INLINE_MATH.finditer(_DISPLAY_MATH.sub("", text))]
        for tex in formulas:
            mathrender.validate(" ".join(tex.split()))


# ------------------------------------------------------------------ parsing
@pytest.mark.parametrize("text, value", [
    ("4.25", 4.25), ("4,25", 4.25), ("−0.53", -0.53), ("5.6e11", 5.6e11), ("5.6E11", 5.6e11),
    ("5.6×10^11", 5.6e11), ("5.6 x 10¹¹", 5.6e11), ("5.6*10^-3", 5.6e-3), ("1,234,567", 1234567),
    ("29 990", 29990), ("0,001418", 0.001418), ("  12  ", 12.0),
])
def test_numbers_people_type(text, value):
    assert parse_number(text) == pytest.approx(value)


def test_an_ambiguous_comma_is_read_both_ways():
    assert parse_candidates("4,246") == [4246.0, 4.246]
    assert check_answer("4,246", 4.246).correct                  # the Turkish reading wins
    assert check_answer("29,990", 29990).correct                 # and the English one here


@pytest.mark.parametrize("text", ["", "abc", "4.2.5", "e11", "∞"])
def test_not_a_number(text):
    assert parse_number(text) is None
    assert check_answer(text, 1.0).verdict is Verdict.INVALID


def test_verdicts():
    assert check_answer("4.3", 4.246, 0.02).verdict is Verdict.CORRECT
    assert check_answer("4.45", 4.246, 0.02).verdict is Verdict.CLOSE
    assert check_answer("42.46", 4.246, 0.02).verdict is Verdict.POWER_OF_TEN
    result = check_answer("5.63e8", 5.627e11, 0.03)
    assert result.verdict is Verdict.POWER_OF_TEN and result.factor == -3
    assert check_answer("0.535", -0.535).verdict is Verdict.SIGN
    assert check_answer("9", 4.246).verdict is Verdict.WRONG
    assert check_answer("0", 0.0).correct


def test_format_answer():
    assert format_answer(4.246) == "4.246"
    assert format_answer(5.627e11) == "5.63 × 10^11"
    assert format_answer(-0.535) == "-0.535"


# ------------------------------------------------------------------ progress
def test_attempts_and_badges(tmp_path):
    from cosmos.achievements import BY_ID
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path / "p.json")
    assert store.record_problem_attempt("p0-proxima", False) is False
    assert store.record_problem_attempt("p0-proxima", True) is True
    assert store.record_problem_attempt("p0-proxima", True) is False      # already solved
    assert store.data.problems_solved["p0-proxima"] == 2
    for problem in SETS[0].problems:
        store.record_problem_attempt(problem.id, True)
    assert BY_ID["problem-set"].is_earned(store, CURRICULUM)
    # Every problem of the set but p0-proxima, which needed two attempts, counts as a first try;
    # state() caps the count at the badge's goal.
    solved_first_try, target = BY_ID["first-try"].state(store, CURRICULUM)
    assert target == 5 and solved_first_try == min(len(SETS[0].problems) - 1, target)
    assert not BY_ID["problem-solver"].is_earned(store, CURRICULUM)
    reloaded = ProgressStore(tmp_path / "p.json")
    assert reloaded.is_problem_solved("p0-andromeda")
    assert re.match(r"p\d-", next(iter(reloaded.data.problem_attempts)))
