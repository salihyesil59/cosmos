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
    assert window.ctx.curriculum.levels[-1].lesson_ids[-1] == "L7.6"


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
    assert window.ctx.curriculum.levels[6].lesson_ids[-1] == "L6.9"
    assert window.ctx.curriculum.levels[5].lesson_ids[-1] == "L5.7"


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
    assert window.review_action.text() == "🔁 " + "Review"      # not due until tomorrow
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
