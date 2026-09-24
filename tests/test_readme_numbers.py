"""E17: the numbers the README advertises are counted from the content, not typed by hand."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tools import content_stats  # noqa: E402


def test_the_readme_is_up_to_date():
    readme = content_stats.README.read_text(encoding="utf-8")
    wrong = content_stats.problems(readme, content_stats.counts())
    assert not wrong, "run `python tools/content_stats.py --write`:\n" + "\n".join(wrong)


def test_a_stale_number_is_caught_and_fixed():
    found = content_stats.counts()
    readme = content_stats.README.read_text(encoding="utf-8")
    stale = readme.replace(f"**{found['lessons']} lessons in", "**3 lessons in", 1)
    stale = stale.replace(f"**{found['badges']} badges**", "**1 badges**", 1)
    wrong = content_stats.problems(stale, found)
    assert any("3 lessons" in line for line in wrong) and any("badges" in line for line in wrong)
    assert content_stats.problems(content_stats.rewrite(stale, found), found) == []


def test_every_simulator_is_listed_by_name():
    readme = content_stats.README.read_text(encoding="utf-8")
    from cosmos.gui.simulators.registry import BUILTIN_IDS

    assert content_stats.simulator_bullets(readme) == len(BUILTIN_IDS)


def test_the_counts_are_sane():
    found = content_stats.counts()
    assert found["levels"] == found["problem sets"]
    assert found["quiz questions"] >= 4 * found["lessons"]
    assert all(value > 0 for value in found.values())
