"""Headless smoke tests: every page and simulator can be opened and used."""

import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
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


def test_cmb_engines(window):
    """S12 offers the exact engine when CAMB is installed, and works without it."""
    from cosmos.physics import camb_backend

    window.navigate("sim:S12")
    pump()
    s12 = window.stack.currentWidget().simulator
    assert s12.engine() == "teaching"
    teaching_peak = s12.spec.peaks[0][0]
    if not camb_backend.available():
        assert not s12.backend.model().item(1).isEnabled()
        assert "not installed" in s12.engine_note.text()
        return
    s12.backend.setCurrentIndex(1)
    pump()
    assert s12.engine() == "camb"
    assert "CAMB" in s12.banner.label.text()
    exact_peak = s12.spec.peaks[0][0]
    assert abs(exact_peak - teaching_peak) / teaching_peak < 0.05    # the two engines agree
    assert len(s12.reference.ell) == len(s12.spec.ell)               # reference uses the same engine
    s12.omega_k.setValue(0.08)
    s12.recompute()
    assert s12.spec.peaks[0][0] > exact_peak                          # open space moves the peak right
    s12.backend.setCurrentIndex(0)
    s12.reset()
    assert s12.engine() == "teaching" and s12.state()["engine"] == "teaching"


def test_tutor_panel(window):
    """The tutor stays off until a key is added, and never calls out on its own."""
    panel = window.tutor
    panel.synchronous = True
    calls = []

    def fake_transport(url, headers, payload):
        calls.append(payload)
        return {"content": [{"type": "text", "text": "Because the wavelength stretches with space."}]}

    panel.transport = fake_transport
    window.navigate("lesson:L2.2")
    pump()
    assert "L2.2" in panel.page_label.text()
    assert not panel.ask_button.isEnabled() and "no API key" in panel.status.text()

    panel.question.setPlainText("Why does light redshift?")
    panel.ask()                                     # without a key nothing may be sent
    assert calls == [] and panel.question.toPlainText() == "Why does light redshift?"

    panel.key_edit.setText("sk-ant-test")
    assert panel.ask_button.isEnabled()
    panel.ask()
    assert len(calls) == 1
    assert "Lesson L2.2" in calls[0]["system"]      # the page the learner is on travels with the question
    assert "redshift" in panel.view.toPlainText().lower()
    assert panel.question.toPlainText() == ""

    panel.include_context.setChecked(False)         # a second question, without the page
    panel.reset_conversation()
    panel.question.setPlainText("And in general?")
    panel.ask()
    assert "Lesson L2.2" not in calls[1]["system"]

    def failing_transport(url, headers, payload):
        raise tutor_error("The API key was refused (401).")

    from cosmos.tutor import TutorError as tutor_error
    panel.transport = failing_transport
    panel.question.setPlainText("Another question")
    panel.ask()
    assert "refused" in panel.status.text()
    assert panel.question.toPlainText() == "Another question"   # the question is given back
    panel.key_edit.clear()
    panel.reset_conversation()


def test_real_data_in_the_simulators(window):
    """Pantheon+ in S16 and SPARC galaxies in S6."""
    window.navigate("sim:S16")
    pump()
    s16 = window.stack.currentWidget().simulator
    s16.sample_box.setCurrentIndex(s16.sample_box.findData("pantheon"))
    pump()
    assert s16.sample.real and len(s16.sample.z) > 1300
    assert "Real measurements" in s16.banner.label.text()
    om, ol = s16.best()
    assert 0.25 < om < 0.42 and 0.5 < ol < 0.8          # the measured cosmology
    s16.cepheid.setChecked(True)                        # an earlier test left the CMB calibration on
    assert 71 < s16.hubble_constant() < 75              # with the SH0ES calibration
    s16.sample_box.setCurrentIndex(s16.sample_box.findData("discovery"))
    pump()
    assert not s16.sample.real and "Simulated data" in s16.banner.label.text()

    window.navigate("sim:S6")
    pump()
    s6 = window.stack.currentWidget().simulator
    assert s6.galaxy is None and s6.galaxy_box.count() > 100
    s6.galaxy_box.setCurrentIndex(s6.galaxy_box.findData("NGC3198"))
    pump()
    assert s6.galaxy.name == "NGC3198" and "SPARC" in s6.banner.label.text()
    assert s6.r_report > 40 and len(s6.data.radius_kpc) == 43
    s6.halo_on.setChecked(False)
    s6.mond.setChecked(False)
    visible_only = s6.rms_residual()
    s6.halo_on.setChecked(True)
    s6._fit_halo()
    assert s6.rms_residual() < visible_only / 3         # the halo rescues the fit
    assert s6.state()["galaxy"] == "NGC3198"
    s6.galaxy_box.setCurrentIndex(0)
    pump()
    assert s6.galaxy is None and s6.r_report == 30.0


def test_mcmc_simulator(window):
    """S19: the chain, its diagnostics and the challenges built on them."""
    window.navigate("sim:S19")
    pump()
    host = window.stack.currentWidget()
    s19 = host.simulator
    assert s19.sample.key == "pantheon"
    state = s19.state()
    assert 0.1 < state["acceptance"] < 0.6
    assert 0.2 < state["om_mean"] < 0.5 and 0.4 < state["ol_mean"] < 0.9
    assert "Ωm" in s19.summary.text() and "Acceptance" in s19.summary.text()

    s19.step_size.setValue(0.004)
    s19.run()
    assert s19.state()["acceptance"] > 0.8
    assert "accepted" in s19.banner.label.text()          # the simulator warns about the tiny steps
    s19.step_size.setValue(0.08)
    s19.run()

    s19.flat.setChecked(True)                             # triggers a fresh run
    assert s19.state()["flat"] and s19.state()["om_error"] < 0.03
    s19.flat.setChecked(False)

    s19.steps.setValue(1500)
    s19.run_many()
    assert s19.state()["chains"] == 4 and s19.state()["rhat"] < 1.15

    s19.animate_button.setChecked(True)                   # reveal the walk step by step
    for _ in range(3):
        s19._tick()
    assert s19.frame > 0
    window.navigate("home")
    assert not s19.animate_button.isChecked()

    window.navigate("sim:S19")
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 4
    s19.step_size.setValue(0.004)
    s19.run()
    bar.go(1)                                             # the "too timid" challenge
    assert bar.check() is True
    s19.step_size.setValue(0.08)
    s19.run()
    bar.go(0)
    assert bar.check() is True


def test_level_seven_lessons(window):
    for lesson_id in ("L7.1", "L7.2"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        assert window.lesson_page.lesson.id == lesson_id
        text = window.lesson_page.browser.toPlainText()
        assert "CSMTOKEN" not in text and "$$" not in text
    assert "S19" in window.ctx.curriculum.lessons["L7.2"].simulators
    assert window.ctx.curriculum.levels[-1].number == 7



def test_second_probe_and_derived_parameters(window):
    """S19 for L7.3: combining with the CMB breaks the degeneracy; derived q0 comes from the samples."""
    window.navigate("sim:S19")
    pump()
    host = window.stack.currentWidget()
    s19 = host.simulator
    s19.flat.setChecked(False)
    s19.steps.setValue(4000)
    s19.step_size.setValue(0.08)
    s19.probe_box.setCurrentIndex(s19.probe_box.findData("none"))
    s19.run()
    alone = s19.state()
    s19.probe_box.setCurrentIndex(s19.probe_box.findData("cmb"))    # runs again with smaller steps
    combined = s19.state()
    assert combined["probe"] == "cmb" and s19.step_size.value() < 0.05
    assert combined["ol_error"] < alone["ol_error"] / 2.5
    assert 0.15 < combined["acceptance"] < 0.7
    assert combined["q0_error"] < alone["q0_error"]
    assert "q0" in s19.summary.text()
    bar = host.challenge_bar
    bar.go(3)
    assert bar.check() is True
    s19.probe_box.setCurrentIndex(s19.probe_box.findData("none"))


def test_distance_ladder_simulator(window):
    """S20: three rungs, an error budget, a Monte Carlo check and a systematic that survives."""
    window.navigate("sim:S20")
    pump()
    host = window.stack.currentWidget()
    s20 = host.simulator
    s20.preset.setCurrentIndex(s20.preset.findData("key_project"))
    state = s20.state()
    assert state["preset"] == "key_project" and state["dominant"] == "parallax"
    assert 4 < state["error_percent"] < 15
    assert "H0" in s20.summary.text()

    s20.n_parallax.setValue(40)
    s20.parallax_error.setValue(20)
    s20.n_hosts.setValue(12)
    s20.recompute()
    state = s20.state()
    assert state["preset"] == "custom" and state["error_percent"] < 3.5
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True

    s20.run_monte_carlo()
    assert s20.state()["mc_runs"] == 300 and s20.state()["mc_mismatch"] < 0.35

    s20.parallax_offset.setValue(20)
    s20.n_flow.setValue(600)
    s20.recompute()
    assert s20.state()["systematic_shift"] > 1.5
    bar.go(1)
    assert bar.check() is True
    for plot in (s20.rungs_plot, s20.budget_plot):
        plot.refresh()
    s20.parallax_offset.setValue(0)


def test_neutrino_mass_in_the_sandbox(window):
    """S18 for L4.7: massive neutrinos are matter, and too much of them fails the report card."""
    window.navigate("sim:S18")
    pump()
    host = window.stack.currentWidget()
    s18 = host.simulator
    s18.preset.set_key("planck18", emit=True)
    assert s18.state()["neutrino_test"] is True
    base_om = s18.state()["omega_m"]
    s18.mnu.setValue(0.5)
    s18.recompute()
    assert s18.state()["omega_m"] > base_om + 0.009 and s18.state()["neutrino_test"] is False
    s18.oc.setValue(s18.oc.value() - (s18.state()["omega_m"] - base_om))
    s18.recompute()
    bar = host.challenge_bar
    assert bar is not None
    bar.go(0)
    assert bar.check() is True
    assert "Neutrino" in s18.report.toPlainText()
    s18.preset.set_key("planck18", emit=True)


def test_new_lessons_render(window):
    for lesson_id in ("L7.3", "L4.7"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        assert window.lesson_page.lesson.id == lesson_id
        text = window.lesson_page.browser.toPlainText()
        assert "CSMTOKEN" not in text and "$$" not in text
    lessons = window.ctx.curriculum.lessons
    assert "S20" in lessons["L7.3"].simulators and "S20" in lessons["L1.1"].simulators
    order = window.ctx.curriculum.ordered_ids
    assert order.index("L4.7") < order.index("L5.1")



def test_problem_sets_page(window):
    """G15: pick a problem, get feedback, reveal hints and the solution, earn progress."""
    window.navigate("problems:p0-proxima")
    pump()
    page = window.problems_page
    assert window.stack.currentWidget() is page and page.current.id == "p0-proxima"
    assert page.tree.topLevelItemCount() == len(window.ctx.curriculum.levels)
    assert "768.07" in page.view.toPlainText()
    assert not page.solution_btn.isEnabled()                   # try first

    page.answer.setText("42.46")
    page.check()
    assert "10^+1" in page.feedback.label.text()               # a power-of-ten slip
    assert page.solution_btn.isEnabled()
    page.show_hint()
    assert "parsec" in page.view.toPlainText()
    page.answer.setText("4,25")
    page.check()
    assert window.ctx.store.is_problem_solved("p0-proxima")
    assert window.ctx.store.data.problems_solved["p0-proxima"] == 2
    page.show_solution()
    assert "Worked solution" in page.view.toPlainText()

    page._step(1)
    assert page.current.id == "p0-sunlight" and page.hints_shown == 0
    page.answer.setText("not a number")
    page.check()
    assert "p0-sunlight" not in window.ctx.store.data.problem_attempts   # invalid input costs nothing

    window.navigate("lesson:L0.2")
    pump()
    assert "route:problems:p0-proxima" in window.lesson_page.guide_markdown()
    window.navigate("progress")
    pump()
    assert window.progress_page.stat_values["problems"].text().startswith("1 /")
    from cosmos.gui.search import search

    assert any(h.route == "problems:p5-bao-angle" for h in search(window.ctx, "BAO ruler"))



def test_survey_designer(window):
    """S21: presets, regimes, dilution, the systematic floor and the challenges."""
    window.navigate("sim:S21")
    pump()
    host = window.stack.currentWidget()
    s21 = host.simulator
    s21.preset.setCurrentIndex(s21.preset.findData("desi_lrg"))
    state = s21.state()
    assert state["tracer"] == "lrg" and state["n_p"] > 3 and 0.3 < state["total_percent"] < 0.5
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True

    s21.tracer.setCurrentIndex(s21.tracer.findData("qso"))       # resets the range and density
    s21.recompute()
    assert s21.state()["n_p"] < 1 and s21.state()["preset"] == "custom"
    s21.density.setValue(3e-4)
    s21.years.setValue(1)
    s21.recompute()
    assert s21.state()["diluted"] and "telescope time" in s21.banner.label.text()
    s21.years.setValue(10)
    s21.recompute()
    bar.go(1)
    assert bar.check() is True

    s21.preset.setCurrentIndex(s21.preset.findData("euclid"))
    s21.floor.setValue(0.4)
    s21.recompute()
    assert s21.state()["stat_below_floor"]
    bar.go(2)
    assert bar.check() is True
    for plot in (s21.distance_plot, s21.tradeoff_plot):
        plot.refresh()
    s21.floor.setValue(0.0)


def test_survey_and_systematics_lessons(window):
    for lesson_id in ("L7.4", "L7.6"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        text = window.lesson_page.browser.toPlainText()
        assert "CSMTOKEN" not in text and "$$" not in text
    assert "S21" in window.ctx.curriculum.lessons["L7.4"].simulators
    assert window.ctx.curriculum.levels[-1].lesson_ids[-2:] == ["L7.6", "L7.7"]


def test_redshift_survey_slice(window):
    """S23: presets, observing effects switched on one at a time, and the challenges."""
    window.navigate("sim:S23")
    pump()
    host = window.stack.currentWidget()
    s23 = host.simulator
    assert s23.preset.currentData() == "sdss"
    state = s23.state()
    assert state["galaxies"] > 800 and state["completeness"] < 0.2
    assert "flux-limited" in s23.banner.label.text()

    s23.preset.setCurrentIndex(s23.preset.findData("truth"))
    truth = s23.state()
    assert truth["rms_velocity"] == 0.0 and truth["finger_length"] == 0.0
    assert truth["completeness"] == 1.0 and "true universe" in s23.banner.label.text()

    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    s23.density.setValue(4e-3)
    s23.recompute()
    bar.go(0)
    assert bar.check() is True

    s23.fingers.setValue(1200)
    s23.recompute()
    assert s23.state()["finger_length"] > 8.0
    bar.go(1)
    assert bar.check() is True
    # Fingers of God stretch the small scales; coherent infall squashes the large ones.
    assert s23.state()["smearing"] < 1.0

    s23.preset.setCurrentIndex(s23.preset.findData("photometric"))
    s23.photo_z.setValue(0.02)
    s23.recompute()
    assert "blurred" in s23.banner.label.text()
    assert s23.state()["redshift_error"] == 0.02

    s23.preset.setCurrentIndex(s23.preset.findData("sdss"))
    s23.magnitude.setValue(17.0)
    s23.density.setValue(3e-2)
    s23.recompute()
    bar.go(2)
    assert bar.check() is True

    header, rows = s23._csv()
    assert len(header) == 6 and len(rows) == len(s23.catalogue)
    for plot in (s23.cone_plot, s23.compare_plot, s23.profile_plot, s23.xi_plot):
        plot.refresh()


def test_simulation_and_estimation_lessons(window):
    for lesson_id in ("L7.5", "L0.7"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        text = window.lesson_page.browser.toPlainText()
        assert "CSMTOKEN" not in text and "$$" not in text
    assert "S23" in window.ctx.curriculum.lessons["L7.5"].simulators
    assert window.ctx.curriculum.levels[0].lesson_ids[-1] == "L0.7"


def test_standard_siren_explorer(window):
    """S22: GW170817, the inclination degeneracy, dark sirens and combining events."""
    window.navigate("sim:S22")
    pump()
    host = window.stack.currentWidget()
    s22 = host.simulator
    assert s22.preset.currentData() == "gw170817"
    state = s22.state()
    assert state["snr"] == pytest.approx(32.4, rel=1e-3)
    assert state["detected"] and state["sky_area"] < 50
    assert 10 < state["h0_percent"] < 25
    assert state["time_in_band"] > 60          # a neutron-star binary chirps for minutes

    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True

    s22.m1.setValue(30.0)
    s22.m2.setValue(30.0)
    s22.distance.setValue(1200.0)
    s22.network.setCurrentIndex(s22.network.findData("o4"))
    s22.host_known.setChecked(False)
    s22.recompute()
    dark = s22.state()
    assert dark["snr"] > 20 and dark["h0_percent"] > 50
    assert dark["time_in_band"] < 5            # heavy binaries are in band for a moment
    assert "dark siren" in s22.banner.label.text()
    bar.go(1)
    assert bar.check() is True

    s22.preset.setCurrentIndex(s22.preset.findData("et"))
    s22.recompute()
    assert s22.state()["h0_percent"] < 2.0
    bar.go(2)
    assert bar.check() is True

    s22.distance.setValue(3000.0)
    s22.network.setCurrentIndex(s22.network.findData("o2"))
    s22.recompute()
    assert not s22.state()["detected"] and "Too quiet" in s22.banner.label.text()

    header, rows = s22._csv()
    assert len(header) == 3 and rows
    for plot in (s22.wave_plot, s22.degeneracy_plot, s22.h0_plot, s22.events_plot):
        plot.refresh()


def test_cmb_polarisation_tabs(window):
    """S12 gained E modes, TE and the B-mode budget for L5.7."""
    window.navigate("sim:S12")
    pump()
    host = window.stack.currentWidget()
    s12 = host.simulator
    state = s12.state()
    assert 350 < state["ee_first_peak"] < 500
    assert 30 < state["ee_peak"] < 60
    assert state["r"] == 0.0 and not state["tensor_above_foregrounds"]

    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True

    s12.tensor_r.setValue(0.1)
    s12.recompute()
    assert s12.state()["tensor_above_foregrounds"]
    bar.go(1)
    assert bar.check() is True

    s12.tensor_r.setValue(0.008)
    s12.dust.setValue(0.0)
    s12.a_lens.setValue(0.1)
    s12.recompute()
    assert s12.state()["tensor_above_foregrounds"]
    bar.go(2)
    assert bar.check() is True

    header, rows = s12._csv_polarisation()
    assert len(header) == 6 and len(rows) == len(s12.pol.ell)
    for plot in (s12.plot, s12.pol_plot, s12.bb_plot, s12.map_plot):
        plot.refresh()
    s12.reset()
    assert s12.state()["r"] == 0.0 and s12.state()["a_lens"] == 1.0


def test_polarisation_and_black_hole_lessons(window):
    for lesson_id in ("L5.7", "L6.9"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        text = window.lesson_page.browser.toPlainText()
        assert "CSMTOKEN" not in text and "$$" not in text
    assert "S22" in window.ctx.curriculum.lessons["L6.9"].simulators
    assert "S22" in window.ctx.curriculum.lessons["L6.5"].simulators
    assert window.ctx.curriculum.levels[6].lesson_ids[-2:] == ["L6.9", "L6.10"]
    assert window.ctx.curriculum.levels[5].lesson_ids[-2:] == ["L5.7", "L5.8"]


def test_review_page_and_a_full_session(window):
    """G16: a missed question comes back, and answering it moves it up a box."""
    from datetime import date, timedelta

    store = window.ctx.store
    store.forget_reviews()
    window.navigate("review")
    pump()
    page = window.review_page
    assert window.stack.currentWidget() is page
    assert "deck is empty" in page.due_label.text()
    assert not page.start_btn.isVisible()

    today = date(2026, 5, 4)
    page.today = lambda: today
    store.record_question("L0.1", 0, False, today - timedelta(days=1))
    store.record_question("L0.2", 2, False, today - timedelta(days=1))
    page.refresh()
    pump()
    assert len(page._items) == 2
    assert "2 question(s) are due" in page.due_label.text()
    assert page.start_btn.isVisible()
    # Every card names the lesson it came from, since a session mixes them.
    assert all(item.source.startswith(item.lesson_id) for item in page._items)

    page.start()
    pump()
    assert page.stack.currentIndex() == 1
    quiz = page.quiz
    assert quiz.review_mode and quiz.source_label.isVisible()
    for _ in range(len(quiz.items)):
        quiz.group.button(quiz.items[quiz.index].question.answer).setChecked(True)
        quiz.check_answer()
        quiz.next_question()
    pump()
    assert quiz.correct == 2
    assert not quiz.next_lesson.isVisible() and not quiz.retry_button.isVisible()
    assert store.data.reviews_cleared >= 1
    assert all(entry["box"] == 2 for entry in store.data.review.values())
    assert store.due_reviews(today) == []

    page.refresh()
    assert "Nothing due today" in page.due_label.text()
    store.forget_reviews()
    del page.today                      # back to the real calendar for the tests that follow
    window.navigate("home")


def test_a_wrong_quiz_answer_joins_the_deck(window):
    """The lesson quiz feeds the review deck without the learner doing anything."""
    store = window.ctx.store
    store.forget_reviews()
    window.navigate("lesson:L0.1")
    pump()
    quiz = window.lesson_page.quiz
    quiz.start()
    wrong = (quiz.items[0].question.answer + 1) % len(quiz.items[0].question.choices)
    quiz.group.button(wrong).setChecked(True)
    quiz.check_answer()
    assert "L0.1#0" in store.data.review
    assert store.data.review["L0.1#0"]["box"] == 1
    window._update_review_action()
    assert window.review_action.text() == "Review"             # not due until tomorrow
    store.forget_reviews()


def test_text_size_and_themes(window):
    """G17: three themes, scalable text, and both are remembered."""
    from cosmos.gui import theme as theme_module
    from cosmos.gui.theme import THEME_ORDER, theme

    assert set(THEME_ORDER) == {"dark", "light", "contrast"}
    start = theme().name
    seen = []
    for _ in range(len(THEME_ORDER)):
        window.toggle_theme()
        seen.append(theme().name)
        assert window.ctx.store.data.theme == theme().name
        assert window.theme_actions[theme().name].isChecked()
    assert sorted(seen) == sorted(THEME_ORDER)
    assert theme().name == start

    window.set_theme("contrast")
    palette = theme().palette
    assert palette.bg == "#000000" and palette.text == "#ffffff"

    window.set_text_size(1.0)
    window.change_text_size(+2)
    assert theme().scale == pytest.approx(1.0 + 2 * theme_module.SCALE_STEP)
    assert window.ctx.store.data.font_scale == theme().scale
    # The stylesheet really does get bigger, and the range is clamped.
    big = QApplication.instance().styleSheet()
    window.set_text_size(0.1)
    assert theme().scale == theme_module.MIN_SCALE
    small = QApplication.instance().styleSheet()
    assert big != small
    window.set_text_size(99)
    assert theme().scale == theme_module.MAX_SCALE
    window.set_text_size(1.0)
    window.set_theme(start)


def test_keyboard_navigation(window):
    """G17: F6 walks the regions and every command is reachable without a mouse."""
    window.navigate("home")
    pump()
    areas = window.focus_areas()
    assert window.sidebar in areas and len(areas) >= 2
    for _ in range(len(areas) + 1):
        window.cycle_focus()
        pump()
        focused = window.focusWidget()
        assert focused is not None
        here = window.focus_areas()
        assert any(a is focused or a.isAncestorOf(focused) for a in here), (
            type(focused).__name__, [type(a).__name__ for a in here])

    rows = dict((text, keys) for text, keys in window.shortcut_rows())
    for command in ("Home", "Find", "Progress", "Review", "Larger text", "Smaller text",
                    "Reset text size", "Move focus to the next area"):
        assert command in rows, command
    assert rows["Reset text size"] == "Ctrl+0"
    assert "F6" == rows["Move focus to the next area"]
    assert len({keys for keys in rows.values()}) == len(rows), "no two commands share a shortcut"

    window.show_shortcuts()
    pump()
    text = window.guide.browser.toPlainText()
    assert "Keyboard shortcuts" in text and "Ctrl+0" in text


def test_printing_lessons_to_pdf(window, tmp_path, monkeypatch):
    """G18: a lesson, a level and the whole course can be saved as PDF."""
    from PySide6.QtWidgets import QFileDialog

    target = tmp_path / "out.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "PDF (*.pdf)")))

    window.navigate("home")
    pump()
    window.export_lesson_pdf()
    assert "Open a lesson first" in window.statusBar().currentMessage()
    assert not target.exists()

    window.navigate("lesson:L0.6")
    pump()
    window.export_lesson_pdf()
    assert "Saved" in window.statusBar().currentMessage()
    assert target.read_bytes().startswith(b"%PDF")
    one_lesson = target.stat().st_size

    window.export_level_pdf()
    assert "Saved" in window.statusBar().currentMessage()
    assert target.stat().st_size > one_lesson, "a whole level must be longer than one lesson"

    # Cancelling the dialog leaves the file alone.
    before = target.stat().st_size
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    window.export_course_pdf()
    assert target.stat().st_size == before


def test_classroom_page_and_mode(window, tmp_path, monkeypatch):
    """G19: the report, the teacher-notes tab and the exports."""
    from PySide6.QtWidgets import QFileDialog

    store = window.ctx.store
    window.navigate("classroom")
    pump()
    page = window.classroom_page
    assert window.stack.currentWidget() is page
    assert not page.mode.isChecked() and not store.data.classroom
    text = page.browser.toPlainText()
    assert "Progress report" in text and "By level" in text
    assert page.guide_markdown()

    # The teacher-notes tab follows the switch, even on a lesson already open.
    window.navigate("lesson:L1.2")
    pump()
    lesson_page = window.lesson_page
    assert not lesson_page.tabs.isTabVisible(lesson_page.teacher_tab)
    page.mode.setChecked(True)
    pump()
    assert store.data.classroom
    assert lesson_page.tabs.isTabVisible(lesson_page.teacher_tab)
    notes = lesson_page.teacher.toPlainText()
    assert "Common misconception" in notes and "Show them" in notes
    page.mode.setChecked(False)
    pump()
    assert not lesson_page.tabs.isTabVisible(lesson_page.teacher_tab)

    # Markdown export, with and without the notes appended.
    plain = tmp_path / "report.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(plain), "Markdown (*.md)")))
    page.export_markdown()
    body = plain.read_text(encoding="utf-8")
    assert body.startswith("# ") and "Teacher notes" not in body

    page.mode.setChecked(True)
    pump()
    page.export_markdown()
    with_notes = plain.read_text(encoding="utf-8")
    assert "Teacher notes" in with_notes and len(with_notes) > 3 * len(body)

    # And the same report as a PDF.
    pdf_path = tmp_path / "report.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(pdf_path), "PDF (*.pdf)")))
    page.export_pdf()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert "Saved" in window.statusBar().currentMessage()

    # In classroom mode a printed lesson carries its notes.
    from cosmos.content.loader import load_teacher_notes
    options = window._pdf_options("Cosmos", "x")
    assert options.teacher_notes and len(options.teacher_notes) == len(load_teacher_notes())
    page.mode.setChecked(False)
    pump()
    assert window._pdf_options("Cosmos", "x").teacher_notes == {}
    store.forget_reviews()


def test_cmb_sky_viewer(window):
    """S24: the real WMAP map, its mask, the filters and the challenges."""
    from cosmos.physics import skymap

    if not skymap.available():
        pytest.skip("run tools/fetch_sky_data.py")

    window.navigate("sim:S24")
    pump()
    host = window.stack.currentWidget()
    s24 = host.simulator
    state = s24.state()
    assert state["masked"] and 60 < state["rms"] < 75
    assert 0.70 < state["sky_fraction"] < 0.80
    assert 0.8 < state["spot_size"] < 3.0
    assert "oldest light" in s24.banner.label.text()

    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3

    # The spot-size challenge works straight away, on the default settings.
    bar.go(1)
    assert bar.check() is True

    # Taking the mask off puts our own galaxy back in the picture.
    s24.use_mask.setChecked(False)
    s24.recompute()
    unmasked = s24.state()
    assert unmasked["sky_fraction"] == pytest.approx(1.0)
    assert unmasked["rms"] > state["rms"]
    assert abs(unmasked["min"]) > abs(state["min"])
    assert "Galaxy is in the picture" in s24.banner.label.text()
    bar.go(0)
    assert bar.check() is True

    # Blurring throws the structure away.
    s24.use_mask.setChecked(True)
    s24.smoothing.setValue(6.0)
    s24.recompute()
    assert s24.state()["rms"] < 35
    bar.go(2)
    assert bar.check() is True

    # The high pass keeps the fine detail instead.
    s24.high_pass.setChecked(True)
    s24.recompute()
    assert s24.state()["high_pass"]
    assert s24.state()["rms"] > 35
    assert "fine detail" in s24.banner.label.text()

    # Both projections draw, and the CSV is a real export.
    s24.smoothing.setValue(0.0)
    s24.high_pass.setChecked(False)
    for index in range(s24.projection.count()):
        s24.projection.setCurrentIndex(index)
        s24.recompute()
        s24.sky_plot.refresh()
    header, rows = s24._csv()
    assert len(header) == 4 and len(rows) > 500
    for plot in (s24.sky_plot, s24.correlation_plot, s24.scales_plot, s24.histogram_plot):
        plot.refresh()


def test_the_mock_can_be_compared_with_the_real_sky(window):
    """E15: S23 gained a tab holding the SDSS slice next to the simulated one."""
    from cosmos.physics import sdss

    if not sdss.available():
        pytest.skip("run tools/fetch_sky_data.py")

    window.navigate("sim:S23")
    pump()
    s23 = window.stack.currentWidget().simulator
    real = s23.real_catalogue()
    assert len(real) > 20_000
    assert real.settings.wedge_deg == pytest.approx(130.0)

    separation, xi = s23.real_correlation()
    assert xi[0] > xi[-1]
    # The mock and the real sky are measured by exactly the same estimator.
    mock_separation, _true, mock_xi = s23._correlations()
    assert len(separation) == len(mock_separation)
    s23.real_plot.refresh()


def test_backing_up_and_restoring_progress(window, tmp_path, monkeypatch):
    """G21: the File menu writes a backup and reads it back, and a bad file changes nothing."""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    store = window.ctx.store
    target = tmp_path / "backup.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(target), "")))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: warnings.append(a[2])))

    store.set_note("lesson:L0.3", "Redshift is a stretch, not a speed.")
    window.backup_progress()
    assert target.exists() and "backed up" in window.statusBar().currentMessage()

    store.set_note("lesson:L0.3", "")
    window.restore_progress()
    pump()
    assert store.note("lesson:L0.3") == "Redshift is a stretch, not a speed."
    assert "restored" in window.statusBar().currentMessage()

    target.write_text("{}", encoding="utf-8")
    window.restore_progress()
    assert warnings and "Nothing was changed" in warnings[-1]
    assert store.note("lesson:L0.3") == "Redshift is a stretch, not a speed."


def test_recombination_explorer(window):
    """S25: Saha against Peebles, the last-scattering shell and the three challenges."""
    window.navigate("sim:S25")
    pump()
    host = window.stack.currentWidget()
    s25 = host.simulator
    state = s25.state()
    assert state["z_half_saha"] > state["z_half"] > state["z_peak"]
    assert state["z_peak"] == pytest.approx(1090, rel=0.03)
    assert 2800 < state["t_peak"] < 3200
    assert "3000 K" in s25.banner.label.text()

    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True                       # Saha is early on the default settings

    s25.t_cmb.setValue(5.45)
    s25.recompute()
    assert "Same temperature" in s25.banner.label.text()
    bar.go(1)
    assert bar.check() is True

    s25._reset()
    s25.omega_b.setValue(0.01)
    s25.recompute()
    assert "Not our universe" in s25.banner.label.text()
    bar.go(2)
    assert bar.check() is True

    for checked in (False, True):
        s25.show_saha.setChecked(checked)
        s25.log_scale.setChecked(checked)
        for plot in (s25.ionisation_plot, s25.visibility_plot, s25.photons_plot):
            plot.refresh()
    header, rows = s25._csv()
    assert len(header) == 6 and len(rows) > 100
    s25._reset()
    s25.recompute()
    assert s25.state()["omega_b_h2"] == pytest.approx(0.0224, abs=1e-4)


def test_far_future(window):
    """S26: every preset, the Big Rip countdown and the three challenges."""
    window.navigate("sim:S26")
    pump()
    host = window.stack.currentWidget()
    s26 = host.simulator
    state = s26.state()
    assert state["preset"] == "ours" and state["fate"] == "accelerates forever"
    assert 0.03 < state["reachable"] < 0.06
    assert state["milestones"] == 9
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True

    fates = {}
    for index in range(s26.preset.count()):
        key = s26.preset.itemData(index)
        if key == "custom":
            continue
        s26.preset.setCurrentIndex(index)
        s26.recompute()
        fates[key] = s26.state()["fate"]
        for plot in (s26.scale_plot, s26.timeline_plot, s26.rip_plot, s26.reach_plot):
            plot.refresh()
    assert fates["phantom"] == fates["mild"] == "ends in a Big Rip"
    assert fates["crunch"] == "recollapses in a Big Crunch"
    assert fates["matter"] == "expands forever"
    assert fates["quintessence"] == "accelerates forever"

    s26.preset.setCurrentIndex(s26.preset.findData("phantom"))
    s26.recompute()
    assert "Big Rip" in s26.banner.label.text()
    assert 10 < s26.state()["earth_seconds"] / 60 < 60           # about half an hour
    bar.go(1)
    assert bar.check() is True

    # Moving a slider makes it the learner's own universe.
    s26.ol.setValue(-0.4)
    s26.recompute()
    assert s26.state()["preset"] == "custom"
    assert "Big Crunch" in s26.banner.label.text()
    bar.go(2)
    assert bar.check() is True
    header, rows = s26._csv()
    assert header[0] == "time_from_now_Gyr" and rows


def test_far_future_lesson(window):
    window.navigate("lesson:L6.10")
    pump()
    assert window.lesson_page.lesson.id == "L6.10"
    text = window.lesson_page.browser.toPlainText()
    assert "CSMTOKEN" not in text and "$$" not in text and "Big Rip" in text
    assert "S26" in window.lesson_page.lesson.simulators


def test_halo_mass_function_explorer(window):
    """S27: the mass function, cluster counts against σ8, the first haloes and the challenges."""
    window.navigate("sim:S27")
    pump()
    host = window.stack.currentWidget()
    s27 = host.simulator
    state = s27.state()
    assert state["ratio"] == pytest.approx(1.0)
    assert 1e12 < state["m_star"] < 1e13
    assert "Bottom up" in s27.banner.label.text()
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3

    s27.sigma8.setValue(0.892)
    s27.recompute()
    assert s27.state()["ratio"] > 2
    assert "big effect" in s27.banner.label.text()
    bar.go(0)
    assert bar.check() is True

    s27._reset()
    s27.redshift.setValue(20.0)
    s27.recompute()
    assert "Cosmic dawn" in s27.banner.label.text()
    assert "below 10⁵" in s27.summary.text()
    bar.go(1)
    assert bar.check() is True

    s27.redshift.setValue(1.0)
    s27.recompute()
    bar.go(2)
    assert bar.check() is True

    for index in range(s27.model.count()):
        s27.model.setCurrentIndex(index)
        s27.recompute()
        for plot in (s27.mass_plot, s27.counts_plot, s27.peaks_plot, s27.time_plot):
            plot.refresh()
    header, rows = s27._csv()
    assert len(header) == 4 and len(rows) == len(s27.current.masses)


def test_dark_ages_lesson(window):
    window.navigate("lesson:L4.8")
    pump()
    text = window.lesson_page.browser.toPlainText()
    assert "CSMTOKEN" not in text and "$$" not in text and "Population III" in text
    assert window.ctx.curriculum.levels[4].lesson_ids[-1] == "L4.8"


def test_dark_matter_detection(window):
    """S29: presets, the verdicts, the simulated run and the three challenges."""
    window.navigate("sim:S29")
    pump()
    host = window.stack.currentWidget()
    s29 = host.simulator
    state = s29.state()
    assert state["preset"] == "lz" and not state["excluded"]
    assert "Hidden" in s29.banner.label.text()
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3
    bar.go(0)
    assert bar.check() is True                    # 50 GeV already sits near the minimum

    # Just above the limit: excluded, not discovered.
    s29.log_sigma.setValue(math.log10(s29.state()["limit"]) + 0.1)
    s29.recompute()
    assert s29.state()["excluded"] and s29.state()["significance"] < 3
    assert "Excluded, but not discovered" in s29.banner.label.text()
    bar.go(2)
    assert bar.check() is True

    s29.log_sigma.setValue(-45.0)
    s29.recompute()
    assert "discovery" in s29.banner.label.text()

    s29.mass.setValue(5.0)
    s29.log_sigma.setValue(-42.0)
    s29.recompute()
    assert "Too light" in s29.banner.label.text()
    s29.preset.setCurrentIndex(s29.preset.findData("silicon"))
    s29.recompute()
    assert s29.state()["signal"] >= 10
    bar.go(1)
    assert bar.check() is True

    s29.threshold.setValue(0.2)
    s29.recompute()
    assert s29.state()["preset"] == "custom"
    s29._rerun()
    for plot in (s29.spectrum_plot, s29.exclusion_plot, s29.run_plot, s29.modulation_plot):
        plot.refresh()
    header, rows = s29._csv()
    assert header[0] == "wimp_mass_GeV" and len(rows) > 50


def test_dark_matter_lesson(window):
    window.navigate("lesson:L3.6")
    pump()
    text = window.lesson_page.browser.toPlainText()
    assert "CSMTOKEN" not in text and "$$" not in text and "axion" in text.lower()
    assert window.ctx.curriculum.levels[3].lesson_ids[-1] == "L3.6"


def test_global_21cm_explorer(window):
    """S28: the standard signal, the EDGES depth, no heating and a late dawn."""
    window.navigate("sim:S28")
    pump()
    host = window.stack.currentWidget()
    s28 = host.simulator
    state = s28.state()
    assert 12 < state["dark_freq"] < 22 and state["emission"] > 5
    assert "Two troughs" in s28.banner.label.text()
    bar = host.challenge_bar
    assert bar is not None and len(host.challenges) == 3

    s28.radio.setValue(1.0)
    s28.recompute()
    assert "As deep as EDGES" in s28.banner.label.text()
    bar.go(0)
    assert bar.check() is True

    s28._reset()
    s28.heating.setValue(0.0)
    s28.recompute()
    assert "Never heated" in s28.banner.label.text()
    bar.go(1)
    assert bar.check() is True

    s28._reset()
    s28.z_alpha.setValue(12.0)
    s28.z_heat.setValue(9.0)
    s28.recompute()
    bar.go(2)
    assert bar.check() is True
    for checked in (False, True):
        s28.show_edges.setChecked(checked)
        for plot in (s28.signal_plot, s28.temperature_plot, s28.coupling_plot):
            plot.refresh()
    header, rows = s28._csv()
    assert header[-1] == "delta_Tb_mK" and len(rows) > 100


def test_galaxy_formation_lesson(window):
    window.navigate("lesson:L5.8")
    pump()
    text = window.lesson_page.browser.toPlainText()
    assert "CSMTOKEN" not in text and "$$" not in text and "feedback" in text.lower()
    assert window.ctx.curriculum.levels[5].lesson_ids[-1] == "L5.8"


def test_glossary_flashcards(window):
    """G22: add terms from the glossary and a lesson, then work through them on the review page."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox

    store = window.ctx.store
    store.forget_flashcards()

    window.navigate("glossary")
    pump()
    page = window.glossary_page
    page.select("parsec")
    pump()
    assert "Add to my flashcards" in page.flash_btn.text()
    page.flash_btn.click()
    assert store.has_flashcard("parsec") and "In my flashcards" in page.flash_btn.text()
    assert "Review (" in window.review_action.text()
    page.flash_btn.click()
    assert not store.has_flashcard("parsec")

    window.navigate("lesson:L0.2")
    pump()
    lesson_page = window.lesson_page
    assert lesson_page.terms_btn.isVisible() and "parsec" in lesson_page.terms
    lesson_page.terms_btn.click()
    assert len(store.data.flashcards) == len(lesson_page.terms)
    lesson_page.terms_btn.click()
    assert "already" in window.statusBar().currentMessage()

    window.navigate("review")
    pump()
    review_page = window.stack.currentWidget()
    assert review_page.flash_btn.isVisible()
    review_page.start_flashcards()
    pump()
    session = review_page.flashcards
    assert review_page.stack.currentWidget() is session
    total = len(session.cards)
    # The keyboard alone: Space turns the card, 2 = knew it, 1 = did not.
    QTest.keyClick(session, Qt.Key_Space)
    assert session.revealed and session.definition.text()
    QTest.keyClick(session, Qt.Key_2)
    session.reveal()
    session.judge(False)
    while not session.done:
        session.reveal()
        session.judge(True)
    assert session.known == total - 1
    assert "All done" in session.term_label.text() and session.back_btn.isEnabled()
    # Everything answered moved on: nothing is due today any more.
    assert store.due_flashcards() == []
    missed = [k for k, e in store.data.flashcards.items() if e["lapses"]]
    assert len(missed) == 1
    session.back_btn.click()
    pump()
    assert review_page.stack.currentIndex() == 0 and not review_page.flash_btn.isVisible()

    import unittest.mock as mock
    with mock.patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
        review_page._forget_flashcards()
    assert store.data.flashcards == {}


def test_study_streak_on_the_home_page(window):
    """G23: steps today, the goal, the streak and the goal announcement."""
    store = window.ctx.store
    window.navigate("home")
    pump()
    home = window.home
    store.data.activity = {}
    store.set_daily_goal(7)                  # a goal no earlier test has announced today
    home.refresh()
    assert "Start a streak" in home.streak_label.text()
    assert "0</b> of 7" in home.goal_label.text()
    for index in range(7):
        store.record_question("L0.3", index % 4, True)
    window.ctx.signals.progressChanged.emit()
    pump()
    assert "1-day streak" in home.streak_label.text()
    assert "goal reached" in home.goal_label.text()
    assert "Daily goal reached" in window.statusBar().currentMessage()
    # The goal can be switched off from the combo box.
    home.goal_combo.setCurrentIndex(home.goal_combo.findData(0))
    assert store.data.daily_goal == 0 and not home.goal_bar.isVisible()
    home.goal_combo.setCurrentIndex(home.goal_combo.findData(10))
    assert store.data.daily_goal == 10


def test_remember_this_cards_and_sheet(window, tmp_path, monkeypatch):
    """G24: every lesson ends in a Remember this card; the cards collect into a sheet and a PDF."""
    from PySide6.QtWidgets import QFileDialog

    for lesson_id in ("L0.1", "L6.9", "L7.5"):
        window.navigate(f"lesson:{lesson_id}")
        pump()
        text = window.lesson_page.browser.toPlainText()
        assert "Remember this" in text and "CSMTOKEN" not in text and "$$" not in text
        assert "What to remember" not in text and "\nSummary\n" not in text

    store = window.ctx.store
    completed = dict(store.data.completed)
    store.data.completed = {"L0.1": "2026-09-01", "L0.2": "2026-09-02"}
    try:
        lessons, only_completed = window.remember_lessons()
        assert only_completed and [lesson.id for lesson in lessons] == ["L0.1", "L0.2"]
        sheet = window.remember_sheet()
        assert "2 completed lesson(s)" in sheet and "### L0.2" in sheet and "### L1.1" not in sheet
        window.show_remember_sheet()
        assert window.guide_dock.isVisible()

        target = tmp_path / "remember.pdf"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
        window.export_remember_pdf()
        assert target.read_bytes().startswith(b"%PDF")
        assert "Saved" in window.statusBar().currentMessage()
    finally:
        store.data.completed = completed
    store.data.completed = {}
    lessons, only_completed = window.remember_lessons()
    assert not only_completed and len(lessons) == len(window.ctx.curriculum.lessons)
    store.data.completed = completed


def test_reading_a_paper_lesson(window):
    window.navigate("lesson:L7.7")
    pump()
    text = window.lesson_page.browser.toPlainText()
    assert "CSMTOKEN" not in text and "$$" not in text and "triangle plot" in text
    assert "Remember this" in text and "From an abstract" in text
    assert window.ctx.curriculum.levels[7].lesson_ids[-1] == "L7.7"


def test_exporting_the_website(window, tmp_path, monkeypatch):
    """E19: File → Export the course as a website builds into a folder of its own."""
    from PySide6.QtWidgets import QFileDialog

    from cosmos.gui.rendering import site

    built = []

    class Report:
        pages = ["index.html"] * 63

    monkeypatch.setattr(site, "build_site", lambda out: built.append(out) or Report())
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path)))
    window.export_website()
    assert built == [tmp_path / "cosmos-website"]
    assert "63 pages" in window.statusBar().currentMessage()

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
    window.export_website()
    assert len(built) == 1                      # cancelled: nothing built


# --------------------------------------------------------------- D1: a calmer interface
def test_the_window_opens_with_nothing_in_the_way(window):
    """D1: the page is the whole window until the learner asks for a panel."""
    from cosmos.progress import UserData

    # A fresh install has every panel closed and the navigation showing.
    assert UserData().panels_open == [] and UserData().nav_hidden is False
    # No panel may take more than a third of a normal window.
    for dock in (window.guide_dock, window.notes_dock, window.tutor_dock):
        assert dock.maximumWidth() <= 420
    # And start-up puts the window back exactly as it was left.
    window.ctx.store.data.panels_open = []
    window._restore_panels()
    pump()
    assert not window.guide_dock.isVisible()
    assert not window.notes_dock.isVisible()
    assert not window.tutor_dock.isVisible()
    window.ctx.store.data.panels_open = ["notes"]
    window._restore_panels()
    pump()
    assert window.notes_dock.isVisible() and not window.guide_dock.isVisible()
    window.notes_dock.hide()
    pump()


def test_the_toolbar_carries_only_what_you_reach_for(window):
    """D1: nine controls, each drawn with an icon rather than an emoji in its label."""
    actions = [a for a in window.toolbar.actions() if not a.isSeparator() and a.text()]
    assert len(actions) == 9
    for kept in (window.nav_action, window.back_action, window.forward_action,
                 window.bookmark_action, window.guide_action, window.notes_action,
                 window.tutor_action):
        assert kept in actions
    # These moved to the menus and the navigation list; they were in three places at once.
    assert window.theme_action not in actions and window.review_action not in actions
    for action in actions:
        assert not action.icon().isNull(), action.text()
        assert all(ord(ch) < 0x2000 for ch in action.text()), action.text()


def test_the_icons_are_drawn_in_code():
    """D1: one pen, one grid, so the set looks the same on every operating system."""
    from cosmos.gui import nav_icons

    for name in nav_icons.GLYPHS:
        assert not nav_icons.icon(name).isNull(), name
    assert nav_icons.icon("home") is nav_icons.icon("home")          # drawn once, then cached
    nav_icons.clear_cache()
    assert nav_icons.icon("home", "#ff0000") is not nav_icons.icon("home", "#00ff00")


def test_the_navigation_opens_one_section_at_a_time(window):
    """D1: the list used to show 58 lessons and 29 simulators all at once."""
    window.navigate("lesson:L2.1")
    pump()
    open_levels = [item for item in window.level_items if item.isExpanded()]
    assert len(open_levels) == 1
    assert window.lesson_items["L2.1"].parent() is open_levels[0]
    assert not window.sims_item.isExpanded()

    window.navigate("sim:S3")
    pump()
    assert window.sims_item.isExpanded() and not window.curriculum_item.isExpanded()

    window.navigate("glossary")
    pump()
    assert not window.sims_item.isExpanded() and not window.curriculum_item.isExpanded()
    # Long titles are shortened, never pushed under a horizontal scrollbar.
    assert window.sidebar.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_the_navigation_folds_away(window):
    """D1: Ctrl+B gives the page the whole window, and the choice is remembered."""
    window.toggle_navigation()
    pump()
    assert not window.nav_dock.isVisible() and window.ctx.store.data.nav_hidden
    window.toggle_navigation()
    pump()
    assert window.nav_dock.isVisible() and not window.ctx.store.data.nav_hidden


def test_a_panel_comes_when_it_is_needed_and_is_remembered(window):
    """D1: clicking a term still explains it, by opening the Guide on the way."""
    store = window.ctx.store
    for dock in (window.guide_dock, window.notes_dock, window.tutor_dock):
        dock.hide()
    pump()
    assert store.data.panels_open == []
    window.navigate("lesson:L1.1")
    pump()
    window.ctx.signals.glossaryRequested.emit("redshift")
    pump()
    assert window.guide_dock.isVisible()
    assert store.data.panels_open == ["guide"]
    window.guide_dock.hide()
    pump()
    assert store.data.panels_open == []


def test_a_lesson_keeps_a_readable_measure(window):
    """D1: text no longer runs the full width of a large screen."""
    from cosmos.gui.widgets.rich_browser import RichBrowser

    window.navigate("lesson:L1.1")
    pump()
    browser = window.lesson_page.browser
    browser.resize(1400, 600)
    pump()
    assert 0 < browser.viewport().width() <= RichBrowser.MEASURE


def test_the_window_comes_back_the_way_it_was_left(window):
    """D2: size, place and panel widths are remembered, like the panels themselves."""
    from PySide6.QtCore import QByteArray

    store = window.ctx.store
    store.data.window_geometry = store.data.window_layout = ""
    window._remember_window()
    assert store.data.window_geometry and store.data.window_layout
    # What was written is exactly what Qt accepts back.
    assert window.restoreGeometry(QByteArray.fromBase64(store.data.window_geometry.encode("ascii")))
    assert window.restoreState(QByteArray.fromBase64(store.data.window_layout.encode("ascii")))

    # A setting damaged by hand is ignored rather than fatal.
    store.data.window_geometry = "these are not bytes"
    store.data.window_layout = "ş"
    window._restore_window()
    pump()
    assert window.isVisible()

    # Closing hides every panel; that must not be read as the learner closing them.
    store.data.window_geometry = store.data.window_layout = ""
    window.show_panel(window.guide_dock)
    pump()
    assert store.data.panels_open == ["guide"]
    window._panels_ready = False            # what closeEvent does
    window.guide_dock.hide()
    pump()
    assert store.data.panels_open == ["guide"]
    window._panels_ready = True
    window.show_panel(window.guide_dock)
    pump()
    window.guide_dock.hide()
    pump()
    assert store.data.panels_open == []
