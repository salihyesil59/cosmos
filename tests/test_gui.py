"""Headless smoke tests: every page and simulator can be opened and used."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_data"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.show()
    app.processEvents()
    yield win
    win.close()


def pump():
    QApplication.instance().processEvents()


def test_home_and_navigation(window):
    window.navigate("home")
    pump()
    assert window.stack.currentWidget() is window.home
    window.navigate("glossary:redshift")
    window.navigate("progress")
    window.navigate("sims")
    pump()
    window.go_back()
    assert window.stack.currentWidget() is window.progress_page
    window.go_forward()
    assert window.stack.currentWidget() is window.sim_hub


def test_every_lesson_renders(window):
    for lesson_id in window.ctx.curriculum.ordered_ids:
        window.navigate(f"lesson:{lesson_id}")
        pump()
        html = window.lesson_page.browser.toHtml()
        assert window.lesson_page.lesson.id == lesson_id
        assert "CSMTOKEN" not in html, f"unreplaced token in {lesson_id}"
        assert "$$" not in window.lesson_page.browser.toPlainText()


def test_every_simulator_opens_and_recomputes(window):
    from cosmos.gui.simulators.registry import SIMULATORS

    for sim_id in SIMULATORS:
        window.navigate(f"sim:{sim_id}")
        pump()
        page = window.stack.currentWidget()
        page.simulator.recompute()
        pump()
        assert page.guide_markdown()


def test_simulator_interactions(window):
    window.navigate("sim:S2")
    s2 = window.stack.currentWidget().simulator
    s2.om.setValue(2.0)
    s2.ode.setValue(0.0)
    s2.recompute()
    assert s2.history.crunch_time is not None
    s2._pin()
    s2.preset.set_key("planck18", emit=True)
    assert abs(s2.history.age - 13.8) < 0.1

    window.navigate("sim:S1")
    s1 = window.stack.currentWidget().simulator
    s1.z.setValue(1090)
    s1.recompute()
    assert any("Age at z" in name for _k, name, _v in s1.results)
    s1.ode.setValue(2.8)
    s1.flat.setChecked(False)
    s1.recompute()  # no-Big-Bang model must not crash

    window.navigate("sim:S5")
    s5 = window.stack.currentWidget().simulator
    s5._best_fit()
    assert 380 < s5.fit.H0 < 520

    window.navigate("sim:S6")
    s6 = window.stack.currentWidget().simulator
    s6._fit_halo()
    assert s6._chi2() < 5

    window.navigate("sim:S4")
    s4 = window.stack.currentWidget().simulator
    s4._start_challenge()
    s4.redshift.setValue(s4.challenge_z)
    s4._check_challenge()
    assert s4.challenge_z is None

    window.navigate("sim:S7")
    s7 = window.stack.currentWidget().simulator
    s7._emit_light()
    for _ in range(20):
        s7._tick()
    assert s7.scale.value() > 1.0
    window.navigate("sim:S3")
    s3 = window.stack.currentWidget().simulator
    s3._jump_to(6)
    pump()


def test_quiz_completion_updates_progress(window):
    lesson_id = window.ctx.curriculum.ordered_ids[0]
    window.navigate(f"lesson:{lesson_id}")
    quiz = window.lesson_page.quiz
    quiz.start()
    for q in window.ctx.curriculum.lessons[lesson_id].quiz:
        quiz.group.button(q.answer).setChecked(True)
        quiz.check_answer()
        quiz.next_question()
    pump()
    assert window.ctx.store.is_completed(lesson_id)
    assert window.ctx.store.next_recommended(window.ctx.curriculum) != lesson_id


def test_theme_toggle_and_tour(window):
    window.toggle_theme()
    pump()
    window.toggle_theme()
    window.start_tour()
    pump()
    from cosmos.gui.widgets.tour import TourOverlay

    overlay = window.findChild(TourOverlay)
    assert overlay is not None
    for _ in range(len(overlay.steps)):
        overlay.go(overlay.index + 1)
        pump()
    assert window.ctx.store.data.tour_completed
