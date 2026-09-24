"""The far future (S26): fates, the Big Rip countdown and the reachable universe."""

import math

import pytest

from cosmos.physics import constants as const
from cosmos.physics import future as fut
from cosmos.physics.cosmology import Cosmology, Fate


def universe(**kw):
    base = dict(H0=70, Om0=0.3, Ode0=0.7, Tcmb0=0.0)
    base.update(kw)
    return Cosmology(**base)


def test_the_rip_agrees_with_caldwell():
    """Caldwell, Kamionkowski & Weinberg (2003): w = −1.5, H0 = 70, Ωm = 0.3 → 22 Gyr."""
    f = fut.future(universe(w0=-1.5))
    assert f.fate is Fate.BIG_RIP
    assert f.end_gyr == pytest.approx(22, rel=0.05)
    assert fut.rip_estimate_gyr(-1.5, 0.3, 70) == pytest.approx(f.end_gyr, rel=0.05)
    times = f.destruction_times()
    year = const.YEAR
    assert times["clusters"] / year == pytest.approx(1e9, rel=0.1)
    assert times["milky-way"] / year == pytest.approx(60e6, rel=0.15)
    assert times["solar-system"] / (86_400 * 30) == pytest.approx(3.4, rel=0.1)   # about three months
    assert times["earth"] / 60 == pytest.approx(24, rel=0.1)                      # about half an hour
    order = [times[s.key] for s in fut.BOUND_SYSTEMS]
    assert order == sorted(order, reverse=True)


def test_the_rip_recedes_as_w_approaches_minus_one():
    ends = [fut.future(universe(w0=w)).end_gyr for w in (-1.5, -1.2, -1.05)]
    assert ends == sorted(ends)
    assert ends[-1] > 150
    assert fut.rip_lead_time(1.0, -1.0) == math.inf


def test_our_future_is_exponential():
    f = fut.future(universe(Om0=0.31, Ode0=0.69))
    assert f.fate is Fate.ACCELERATES_FOREVER and not f.ends
    assert f.efold_gyr == pytest.approx(1 / math.sqrt(0.69) * universe().hubble_time, rel=1e-6)
    # About 5% of the galaxies we see can still be reached (event horizon 16.7, particle 46 Gly).
    assert 0.03 < f.reachable_now < 0.06
    assert f.reach[-1] < f.reach[0]
    assert all(f.happens(m) for m in fut.MILESTONES)


def test_crunch_and_deceleration():
    crunch = fut.future(universe(Om0=0.3, Ode0=-0.3))
    assert crunch.fate is Fate.BIG_CRUNCH and 30 < crunch.end_gyr < 100
    assert crunch.a[-1] == pytest.approx(0.0)
    assert not crunch.happens(fut.MILESTONES[4])                # no star formation to end
    matter = fut.future(universe(Om0=1.0, Ode0=0.0))
    assert matter.fate is Fate.EXPANDS_FOREVER and not matter.ends
    assert len(matter.reach) == 0                               # no event horizon
    accelerating_only = [m for m in fut.MILESTONES if m.needs_acceleration]
    assert accelerating_only and not any(matter.happens(m) for m in accelerating_only)


def test_hawking_lifetimes():
    assert fut.hawking_lifetime_years(1.0) == pytest.approx(2.1e67, rel=0.05)
    assert fut.hawking_lifetime_years(1e11) / fut.hawking_lifetime_years(1.0) == pytest.approx(1e33)
    years = [m.years_from_now for m in fut.MILESTONES]
    assert years == sorted(years)
