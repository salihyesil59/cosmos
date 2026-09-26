"""V4: the engine's own report card, and the promise that it is current.

The Data & methods page tells a reader that the physics is checked against
astropy, against closed forms and against published numbers. These tests are what
makes that sentence true: every check in the catalogue is run here, on every
change, and the numbers the app ships are compared with a fresh run so that the
shipped ones cannot quietly go stale.
"""

from __future__ import annotations

import pytest

from cosmos import validation

pytest.importorskip("astropy", reason="the astropy comparisons need astropy installed")


@pytest.fixture(scope="module")
def results():
    return {r.check.id: r for r in validation.run_all()}


def test_every_check_can_be_run(results):
    assert set(results) == {c.id for c in validation.CHECKS}
    assert len(results) == len(validation.RUNNERS)


def test_the_engine_passes_every_check(results):
    failures = [
        f"{r.check.quantity}: {r.check.format(r.worst)} against a limit of "
        f"{r.check.format(r.check.tolerance)}"
        for r in results.values() if not r.passed
    ]
    assert not failures, "the physics engine disagrees with its references:\n" + "\n".join(failures)


def test_the_catalogue_describes_itself_properly():
    kinds = {validation.AGAINST_ASTROPY, validation.AGAINST_CLOSED_FORM, validation.AGAINST_PUBLISHED}
    seen = set()
    for check in validation.CHECKS:
        assert check.id not in seen, f"duplicate id {check.id}"
        seen.add(check.id)
        assert check.quantity and check.reference and check.detail, check.id
        assert check.against in kinds, check.id
        assert check.tolerance > 0, check.id
        assert check.relative or check.unit or check.id == "helium_abundance", check.id
    assert kinds <= {c.against for c in validation.CHECKS}, "a whole kind of check disappeared"


def test_the_astropy_checks_are_not_the_only_ones():
    """A comparison with one other implementation proves less than it looks.

    If astropy and this engine shared a mistake, only the closed forms and the
    published numbers would notice.
    """
    independent = [c for c in validation.CHECKS if c.against != validation.AGAINST_ASTROPY]
    assert len(independent) >= 6


# ------------------------------------------------------- the shipped record

def test_the_shipped_numbers_are_there_and_complete():
    record = validation.read_record()
    assert record is not None, "cosmos/data/validation.json is missing or unreadable"
    assert record["measured"], "the record does not say when it was measured"
    assert set(record["worst"]) == {c.id for c in validation.CHECKS}, (
        "the recorded checks and the catalogue have drifted apart; "
        "run tools/record_validation.py"
    )


def test_the_shipped_numbers_still_match_a_fresh_run(results):
    """What a packaged build shows must be what the engine does today.

    Floating-point results move a little between platforms, so the rule is not
    equality: a recorded number must still pass its own tolerance, and must not
    differ from a fresh run by more than that tolerance. That is loose enough for
    the last decimal place and tight enough to catch a number left behind by a
    change to the engine.
    """
    record = validation.read_record()
    stale = []
    for check_id, recorded in record["worst"].items():
        live = results[check_id].worst
        tolerance = results[check_id].check.tolerance
        if recorded > tolerance or abs(recorded - live) > tolerance:
            stale.append(f"{check_id}: recorded {recorded:.4g}, now {live:.4g}")
    assert not stale, ("the shipped validation numbers are out of date; "
                       "run tools/record_validation.py\n" + "\n".join(stale))


# ------------------------------------------------------- without astropy

def test_the_report_degrades_honestly_without_astropy(monkeypatch):
    """A packaged build has no astropy, and must say so rather than pretend."""
    monkeypatch.setattr(validation, "astropy_available", lambda: False)
    runnable = [c for c in validation.CHECKS if validation.runnable(c)]
    assert runnable, "nothing at all can be checked without astropy"
    assert all(c.against != validation.AGAINST_ASTROPY for c in runnable)
    # The ones that cannot run are exactly the astropy comparisons, and the
    # record still carries their numbers for the app to show.
    blocked = [c for c in validation.CHECKS if not validation.runnable(c)]
    record = validation.read_record()
    assert blocked and all(c.id in record["worst"] for c in blocked)


def test_running_without_astropy_still_returns_results(monkeypatch):
    monkeypatch.setattr(validation, "astropy_available", lambda: False)
    offline = validation.run_all()
    assert offline and all(r.passed for r in offline)


def test_a_partial_run_refuses_to_be_recorded(monkeypatch, tmp_path):
    """Recording half the checks would ship a record that looks complete."""
    monkeypatch.setattr(validation, "astropy_available", lambda: False)
    with pytest.raises(RuntimeError, match="partial"):
        validation.write_record(tmp_path / "validation.json")
    assert not (tmp_path / "validation.json").exists()


# --------------------------------------------------------------- formatting

def test_a_result_is_readable():
    check = next(c for c in validation.CHECKS if c.id == "planck18_age")
    assert check.format(0.00689) == "0.00689 Gyr"
    relative = next(c for c in validation.CHECKS if c.id == "expansion_rate")
    assert relative.format(5.3e-14) == "5.30e-14"
    assert relative.format(0.0) == "0"
