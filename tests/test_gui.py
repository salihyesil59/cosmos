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


def test_structure_simulators(window):
    window.navigate("sim:S12")
    s12 = window.stack.currentWidget().simulator
    s12.omega_k.setValue(-0.08, emit=False)
    s12.recompute()
    assert s12.spec.peaks[0][0] < s12.reference.peaks[0][0]
    s12.reset()
    assert abs(s12.spec.peaks[0][0] - s12.reference.peaks[0][0]) < 1

    window.navigate("sim:S13")
    s13 = window.stack.currentWidget().simulator
    s13.resolution.setCurrentIndex(0)
    s13.restart()
    s13._advance(40)
    assert s13.sim.growth > 0.08
    s13.warm.setChecked(True)
    s13.restart()
    assert s13.sim.config.cutoff > 0
    s13.play.setChecked(True)
    window.navigate("home")
    assert not s13.play.isChecked()  # animation stops when leaving the page

    window.navigate("sim:S14")
    s14 = window.stack.currentWidget().simulator
    for index in range(s14.kind.count()):
        s14.kind.setCurrentIndex(index)
        s14.background.setCurrentIndex(index % 2)
        s14.recompute()
        pump()
    s14._move_source(0.0, 0.0)
    s14.z_source.setValue(0.2, emit=False)
    s14.z_lens.setValue(1.0, emit=False)
    s14.recompute()  # source in front of the lens must show a warning, not crash
    assert s14.banner.isVisibleTo(s14)


def test_advanced_simulators(window):
    import math

    window.navigate("sim:S8")
    s8 = window.stack.currentWidget().simulator
    s8.side.setValue(math.pi / 2, emit=False)
    s8.omega_k.setValue(0.0, emit=False)
    s8.recompute()
    assert "Closed: <b>269.9°" in s8.summary.text()  # side 1.57 ≈ π/2: an octant of the sphere

    window.navigate("sim:S9")
    s9 = window.stack.currentWidget().simulator
    for index in range(s9.coords.count()):
        s9.coords.setCurrentIndex(index)
        s9.observe.setValue(0.5 + index, emit=False)
        s9.recompute()
    s9.om.setValue(0.05, emit=False)
    s9.ode.setValue(1.5, emit=False)
    s9.recompute()  # no Big Bang: warning instead of a crash
    assert s9.data is None and s9.banner.isVisibleTo(s9)

    window.navigate("sim:S15")
    s15 = window.stack.currentWidget().simulator
    for index in range(s15.potential.count()):
        s15.potential.setCurrentIndex(index)
        pump()
    s15.potential.setCurrentIndex(0)  # quadratic
    s15.recompute()
    assert not s15.result.consistent
    s15._rewind()
    s15.play.setChecked(True)
    for _ in range(5):
        s15._tick()
    window.navigate("home")
    assert not s15.play.isChecked()

    window.navigate("sim:S16")
    s16 = window.stack.currentWidget().simulator
    s16.sample_box.setCurrentIndex(1)
    s16.recompute()
    cepheid = s16.hubble_constant()
    s16.inverse.setChecked(True)
    s16.recompute()
    assert cepheid - s16.hubble_constant() > 3
    s16.flat.setChecked(True)
    s16.recompute()

    window.navigate("sim:S18")
    s18 = window.stack.currentWidget().simulator
    s18.preset.set_key("planck18", emit=True)
    assert all(check.passed for check in s18.checks)
    s18.oc.setValue(0.0, emit=False)
    s18.w0.setValue(-1.3, emit=False)
    s18.recompute()
    assert sum(1 for check in s18.checks if check.passed is False) >= 2
    s18.radiation.setChecked(False)
    s18.recompute()

    window.navigate("sim:S6")
    s6 = window.stack.currentWidget().simulator
    s6.mond.setChecked(True)
    s6.recompute()
    assert s6._chi2() < 10
    s6._fit_halo()
    assert not s6.mond.isChecked()


def test_history_simulators(window):
    import math

    window.navigate("sim:S10")
    s10 = window.stack.currentWidget().simulator
    s10.log_time.setValue(0.0)                       # one second after the Big Bang
    assert "10<sup>9</sup> K" in s10.readout.text()          # 1e10 K, written as 9.99 × 10^9
    assert "light-seconds" in s10.readout.text()             # the horizon is a couple of light-seconds
    assert "Neutrino decoupling" in s10.banner.label.text()
    s10.epoch_box.setCurrentIndex(s10.epoch_box.findData("Recombination and the CMB"))
    s10._jump(s10.epoch_box.currentIndex())
    assert abs(s10.log_time.value() - math.log10(3.7e5 * 3.15576e7)) < 0.01
    assert "Recombination" in s10.banner.label.text()
    s10.play.setChecked(True)
    for _ in range(5):
        s10._tick()
    window.navigate("home")
    assert not s10.play.isChecked()

    window.navigate("sim:S11")
    s11 = window.stack.currentWidget().simulator
    s11._from_deuterium()
    assert 5.5 < s11.eta.value() < 6.5                # deuterium agrees with the CMB baryon density
    assert "lithium" in s11.banner.label.text()       # helium and deuterium fit, lithium does not
    planck_yp = float(s11.ab.yp)
    s11.delta_neff.setValue(2.0)
    pump()
    s11.recompute()
    assert float(s11.ab.yp) > planck_yp + 0.02
    assert "does not match" in s11.banner.label.text()
    s11._reset_physics()
    assert s11.delta_neff.value() == 0.0

    window.navigate("sim:S17")
    s17 = window.stack.currentWidget().simulator
    for key in ("olbers", "age", "lifetimes", "expanding"):
        s17.scenario.setCurrentIndex(s17.scenario.findData(key))
        pump()
    s17.scenario.setCurrentIndex(s17.scenario.findData("olbers"))
    pump()
    assert s17.sky.coverage == 1.0 and "paradox" in s17.banner.label.text()
    s17.finite_age.setChecked(True)
    s17.age.setValue(30.0)
    s17.recompute()
    assert s17.sky.coverage < 0.5
    assert s17.scenario.currentData() == "custom"     # editing a control switches to Custom
    s17._new_sky()


def test_reference_search_and_notes(window):
    store = window.ctx.store

    window.navigate("reference")
    ref = window.reference_page
    assert len(ref.matching_formulas()) > 40
    ref.search.setText("Friedmann")
    assert 0 < len(ref.matching_formulas("Friedmann")) < len(ref.formulas)   # the group plus its members
    assert "Friedmann" in ref.formula_view.toPlainText()
    ref.search.clear()
    ref.tabs.setCurrentIndex(1)
    ref.converter.family.setCurrentText("Length")
    ref.converter.unit.setCurrentText("parsecs")
    ref.converter.amount.setValue(1.0)
    assert "3.26156" in ref.converter.result.text()          # 1 pc in light-years
    ref.tabs.setCurrentIndex(2)
    assert "Planck 2018" in ref.models_view.toPlainText()

    window.search_box.setText("nucleosynthesis")
    window.search_box.returnPressed.emit()
    pump()
    assert window.stack.currentWidget() is window.search_page
    assert window.search_page.list.count() > 3
    window.search_page.list.setCurrentRow(0)
    window.search_page._open_item(window.search_page.list.item(0))
    pump()
    assert window.stack.currentWidget() in (window.lesson_page, window.reference_page, window.glossary_page)

    window.navigate("lesson:L1.1")
    window.notes.editor.setPlainText("A parsec is 3.26 light-years.")
    window.notes.save()
    assert store.note("lesson:L1.1") == "A parsec is 3.26 light-years."
    window.toggle_bookmark()
    assert store.is_bookmarked("lesson:L1.1") and "Bookmarked" in window.bookmark_action.text()
    window.navigate("notes")
    pump()
    assert "1 bookmarks · 1 notes" in window.notes_page.subtitle.text()
    assert "3.26 light-years" in window.notes_page.as_markdown()
    window.notes_page._remove_bookmark("lesson:L1.1")
    assert not store.is_bookmarked("lesson:L1.1")

    window.navigate("search:xyzzy-not-a-word")
    pump()
    assert "Nothing found" in window.search_page.count.text()
    window.navigate("glossary")                              # notes are disabled where they make no sense
    window.navigate("search:redshift")
    assert window.notes.route == ""


def test_intuitive_view_and_challenges(window):
    store = window.ctx.store

    window.navigate("lesson:L2.3")
    page = window.lesson_page
    full_text = page.browser.toPlainText()
    page.view_buttons.button(0).click()                       # Intuitive
    pump()
    assert store.data.math_view == "intuitive"
    assert "Intuitive view" in page.browser.toPlainText()
    assert page.hidden_counts(page.lesson) == (8, 1)          # 8 formulas, 1 derivation callout
    window.navigate("lesson:L4.3")
    pump()
    assert page.view_buttons.button(0).isChecked()            # the choice follows the learner
    page.view_buttons.button(1).click()
    assert store.data.math_view == "full" and page.browser.toPlainText() != ""
    window.navigate("lesson:L2.3")
    pump()
    assert page.browser.toPlainText() == full_text

    window.navigate("sim:S17")
    host = window.stack.currentWidget()
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    sim = host.simulator
    sim.scenario.setCurrentIndex(sim.scenario.findData("olbers"))   # an earlier test left it elsewhere
    pump()
    bar.go(0)
    assert bar.check() is True                                # Olbers' universe: the sky is fully covered
    assert store.is_challenge_done("S17", "blazing-sky")
    assert "challenger" in store.data.achievements
    bar.go(2)
    assert bar.check() is False                               # not set up for the expansion challenge
    bar.show_hint()
    assert "Hint" in bar.feedback.label.text()
    sim.scenario.setCurrentIndex(sim.scenario.findData("expanding"))
    pump()
    assert bar.check() is True
    assert "Challenges" in host.guide_markdown()

    window.navigate("sim:S1")
    calculator = window.stack.currentWidget()
    calculator.simulator.preset.set_key("planck18", emit=True)
    calculator.simulator.z.setValue(1090)
    calculator.simulator.recompute()
    calculator.challenge_bar.go(0)
    assert calculator.challenge_bar.check() is True


def test_history_page(window):
    window.navigate("history")
    pump()
    page = window.history_page
    assert len(page.matching_events()) > 25
    assert 1998 in [e.year for e in page.matching_events("supernovae")]
    assert page.matching_scientists("Leavitt")[0].name.endswith("Leavitt")
    page.search.setText("dark matter")
    pump()
    assert 0 < len(page.matching_events("dark matter")) < 10
    page.search.clear()
    page.tabs.setCurrentIndex(1)
    page.show_scientist(page.scientists[0])
    assert "Copernicus" in page.person_view.toPlainText()
    assert "history" in window.ctx.store.data.pages_seen

    window.navigate("progress")
    pump()
    assert "badges earned" in window.progress_page.badge_summary.text()
    assert window.progress_page.badge_widgets["historian"][3].text().startswith("Earned")
