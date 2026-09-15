"""Catalogue of simulators with their guidance texts."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimulatorInfo:
    id: str
    title: str
    tagline: str
    description: str
    how_to_use: list[str]
    things_to_try: list[str]
    lessons: list[str]
    module: str
    class_name: str
    icon: str = "◆"
    extra: dict = field(default_factory=dict)

    def create(self, **kwargs):
        cls = getattr(importlib.import_module(self.module), self.class_name)
        return cls(self, **kwargs)


SIMULATORS: dict[str, SimulatorInfo] = {
    s.id: s
    for s in [
        SimulatorInfo(
            id="S1",
            title="Cosmology Calculator",
            tagline="Ages, distances and more for any redshift.",
            description=(
                "Choose a cosmological model and a redshift z. The calculator tells you how old the "
                "universe was when the light left the object, how long the light travelled, and the "
                "different 'distances' astronomers use."
            ),
            how_to_use=[
                "Pick a model from <b>Preset</b> (Planck 2018 is today's best estimate) or type your own values.",
                "Enter the <b>redshift z</b> of the object you are interested in.",
                "Read the results table. Click any row to see what that quantity means.",
                "Use the plots to see how each quantity changes with redshift.",
            ],
            things_to_try=[
                "Set z = 1100: this is the cosmic microwave background. How old was the universe?",
                "Compare the comoving and light-travel distances at z = 3. Why is one larger?",
                "Switch to Einstein–de Sitter. Is the universe older or younger than in Planck 2018?",
            ],
            lessons=["L0.6", "L1.2", "L1.5", "L2.1", "L2.2", "L2.6", "L2.7", "L3.4", "L3.5", "L4.5"],
            module="cosmos.gui.simulators.calculator",
            class_name="CalculatorSimulator",
            icon="∑",
        ),
        SimulatorInfo(
            id="S2",
            title="Expansion History Explorer",
            tagline="How matter and dark energy shape the past and future.",
            description=(
                "Adjust how much matter and dark energy the universe contains and watch the scale "
                "factor a(t) change. The Ωm–ΩΛ map shows which combinations lead to eternal "
                "expansion, a Big Crunch or no Big Bang at all."
            ),
            how_to_use=[
                "Move the <b>Ωm</b> and <b>ΩΛ</b> sliders, or click anywhere on the Ωm–ΩΛ map.",
                "The upper plot shows the size of the universe over time; today is at t = 0 where a = 1.",
                "Press <b>Pin curve</b> to keep the current curve for comparison.",
                "Read the summary for the universe's age, geometry and fate.",
            ],
            things_to_try=[
                "Find the Big Crunch region: increase Ωm above 1 with ΩΛ = 0.",
                "Pin Planck 2018, then set ΩΛ = 0 with Ωm = 0.3. Which universe is older?",
                "Cross the dashed 'accelerating' line and watch the curve's shape today.",
            ],
            lessons=["L2.3", "L2.4", "L2.5", "L2.6", "L3.3", "L3.4", "L3.5"],
            module="cosmos.gui.simulators.expansion",
            class_name="ExpansionSimulator",
            icon="⤴",
        ),
        SimulatorInfo(
            id="S3",
            title="Powers of Ten Zoom",
            tagline="From a human to the observable universe.",
            description=(
                "Zoom out from human size to the whole observable universe, one power of ten at a time. "
                "Every object is drawn to scale for the current field of view."
            ),
            how_to_use=[
                "Drag the <b>zoom slider</b> or scroll the mouse wheel over the view.",
                "Press <b>Play</b> to fly out automatically; press again to stop.",
                "Use <b>Jump to</b> to go straight to an object.",
                "The panel on the right describes what is visible and how long light takes to cross the view.",
            ],
            things_to_try=[
                "How many powers of ten separate the Earth from the Sun's size?",
                "Find the scale where light needs one year to cross the view.",
                "Notice how empty space is between stars compared with between galaxies.",
            ],
            lessons=["L0.1", "L0.2", "L1.4"],
            module="cosmos.gui.simulators.powers_of_ten",
            class_name="PowersOfTenSimulator",
            icon="⊙",
        ),
        SimulatorInfo(
            id="S4",
            title="Spectrum & Redshift Simulator",
            tagline="See spectral lines shift with motion and expansion.",
            description=(
                "Atoms absorb light at precise wavelengths, leaving dark lines in a spectrum. Move the "
                "source or expand the universe and watch the lines slide toward the red (or blue)."
            ),
            how_to_use=[
                "Choose <b>Doppler motion</b> (a moving source) or <b>Cosmic expansion</b> (a distant galaxy).",
                "Move the slider. The lower strip shows the observed spectrum; the upper one is the laboratory spectrum.",
                "Lines that leave the visible range continue into the infrared (grey area).",
                "Try the <b>Mystery galaxy</b> challenge to measure a redshift yourself.",
            ],
            things_to_try=[
                "At what redshift does the red Hα line leave the visible range?",
                "Make the source approach you: which way do the lines move?",
                "At z = 2, how big was the universe compared with today?",
            ],
            lessons=["L0.3", "L1.5", "L2.2"],
            module="cosmos.gui.simulators.spectrum",
            class_name="SpectrumSimulator",
            icon="≋",
        ),
        SimulatorInfo(
            id="S5",
            title="Hubble Diagram Fitter",
            tagline="Measure the expansion rate from real data.",
            description=(
                "Plot galaxy velocities against distances and fit a straight line through the origin. "
                "Its slope is the Hubble constant H0, and 1/H0 estimates the age of the universe."
            ),
            how_to_use=[
                "Select a <b>data set</b>: Hubble's original 1929 data or a simulated modern sample.",
                "Move the <b>H0 slider</b> until the line follows the points; watch the residuals shrink.",
                "Press <b>Find best fit</b> to let least squares find the optimal slope.",
                "Compare the Hubble time 1/H0 with the true age of the universe (13.8 Gyr).",
            ],
            things_to_try=[
                "Fit Hubble's data. Why is his H0 about seven times too large?",
                "Notice the galaxies with negative velocities in 1929: which ones are they?",
                "Fit the modern sample and compute 1/H0 in billions of years.",
            ],
            lessons=["L0.5", "L1.1", "L1.2"],
            module="cosmos.gui.simulators.hubble_fit",
            class_name="HubbleFitSimulator",
            icon="⟋",
        ),
        SimulatorInfo(
            id="S6",
            title="Galaxy Rotation Curve",
            tagline="Uncover dark matter from how galaxies spin.",
            description=(
                "Stars orbit the centre of a galaxy. If only visible matter pulled on them, distant stars "
                "would move slowly. Build a galaxy from a bulge, a disk and a dark matter halo and compare "
                "with a measured-style rotation curve."
            ),
            how_to_use=[
                "Adjust the <b>bulge</b> and <b>disk</b> masses: these are the stars and gas you can see.",
                "Turn the <b>dark matter halo</b> on and change its mass.",
                "Compare the total curve with the data points.",
                "Press <b>Fit halo to data</b> to find the halo mass that matches best.",
            ],
            things_to_try=[
                "Switch off the halo: how does the curve behave at 30 kpc?",
                "How much dark matter lies inside 30 kpc compared with visible matter?",
                "Can you fit the data with a heavier disk and no halo? Why not?",
            ],
            lessons=["L3.2"],
            module="cosmos.gui.simulators.rotation_curve",
            class_name="RotationCurveSimulator",
            icon="◎",
        ),
        SimulatorInfo(
            id="S7",
            title="Balloon & Raisin-Bread Expansion",
            tagline="Why every galaxy sees all others moving away.",
            description=(
                "Galaxies sit on a grid that stretches as the universe expands. Pick any galaxy as your "
                "home: all others recede from it, faster the farther they are. Light travelling between "
                "galaxies is stretched too."
            ),
            how_to_use=[
                "Press <b>Play</b> to expand the universe; <b>Reset</b> returns to the start.",
                "<b>Click a galaxy</b> to stand on it. Arrows show how others move as seen from there.",
                "Press <b>Emit light</b> to send a wave and watch its wavelength stretch.",
                "Toggle the comoving grid to see that galaxies keep their grid positions.",
            ],
            things_to_try=[
                "Choose a galaxy at the edge. Is the pattern of arrows any different?",
                "Compare an arrow twice as long with the distance: is the ratio the same?",
                "Emit light, wait until the scale factor doubles, and read the redshift.",
            ],
            lessons=["L1.3", "L2.1", "L2.2"],
            module="cosmos.gui.simulators.balloon",
            class_name="BalloonSimulator",
            icon="◌",
        ),
        SimulatorInfo(
            id="S12",
            title="CMB Power Spectrum Explorer",
            tagline="How the universe's ingredients shape the CMB peaks.",
            description=(
                "The pattern of hot and cold spots in the cosmic microwave background encodes the geometry and "
                "contents of the universe. Change ordinary matter, dark matter, curvature and the initial "
                "fluctuations, and watch the acoustic peaks and the simulated sky respond."
            ),
            how_to_use=[
                "Move a slider in <b>Contents of the universe</b>; the blue curve is your universe, the dashed curve "
                "the Planck 2018 model.",
                "Read the <b>peak positions</b> and the acoustic angle in the results panel.",
                "Open the <b>What the sky looks like</b> tab to compare simulated sky patches.",
                "Press <b>Reset to Planck 2018</b> to start again.",
            ],
            things_to_try=[
                "Make space closed (Ωk = −0.1): do the spots on the sky look larger or smaller?",
                "Double Ωb h². Which peaks grow and which shrink?",
                "Set τ = 0.15. Which part of the spectrum is suppressed?",
            ],
            lessons=["L5.1", "L5.2", "L2.5", "L4.4"],
            module="cosmos.gui.simulators.cmb_spectrum",
            class_name="CMBSpectrumSimulator",
            icon="∿",
        ),
        SimulatorInfo(
            id="S13",
            title="2D N-body Structure Formation",
            tagline="Watch gravity build the cosmic web from tiny ripples.",
            description=(
                "Tens of thousands of dark matter particles start almost uniformly spread, with tiny ripples. "
                "Gravity amplifies the ripples into sheets, filaments and halos that merge into ever larger "
                "structures. Compare the growth with linear theory and try warm dark matter."
            ),
            how_to_use=[
                "Press <b>Play</b>. Time is measured by the growth factor D; D = 1 corresponds to today.",
                "Watch the lower plot: at first the density contrast follows linear theory, then gravity takes over.",
                "Change the <b>spectral index</b> or choose <b>warm dark matter</b>, then press <b>Apply and restart</b>.",
                "A different <b>random seed</b> gives a different universe with the same statistics.",
            ],
            things_to_try=[
                "When does the simulation first deviate from the linear-theory line?",
                "Compare n = −2 with n = 0: which one forms large filaments, which one many small clumps?",
                "Run the same seed with warm dark matter. What happens to the smallest halos?",
            ],
            lessons=["L5.3", "L5.4", "L5.5", "L1.4"],
            module="cosmos.gui.simulators.nbody_sim",
            class_name="NBodySimulator",
            icon="⁂",
        ),
        SimulatorInfo(
            id="S14",
            title="Gravitational Lensing Simulator",
            tagline="Bend light with galaxies, clusters and black holes.",
            description=(
                "Mass bends the paths of light rays. Put a point mass, a galaxy or a galaxy cluster in front of "
                "distant galaxies and see multiple images, arcs and Einstein rings. The Einstein radius uses real "
                "cosmological distances, so the ring's size weighs the lens."
            ),
            how_to_use=[
                "Choose a <b>lens type</b> and set its mass or velocity dispersion.",
                "<b>Drag</b> inside the image to move the background galaxy; the orange cross marks its true position.",
                "Change the <b>lens and source redshifts</b> and watch the Einstein radius in the measurements.",
                "Switch to <b>a field of galaxies</b> to see how a cluster distorts many galaxies at once.",
            ],
            things_to_try=[
                "Place the source exactly behind the lens: what shape appears?",
                "Tick <b>Switch the lens off</b> to see the sky as it would look without gravity.",
                "Keep the lens mass fixed and move the lens redshift: where is lensing strongest?",
            ],
            lessons=["L5.6", "L3.2", "L0.4"],
            module="cosmos.gui.simulators.lensing_sim",
            class_name="LensingSimulator",
            icon="⊚",
        ),
    ]
}
