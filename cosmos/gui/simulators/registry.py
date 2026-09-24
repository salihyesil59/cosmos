"""Catalogue of simulators with their guidance texts."""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from cosmos.i18n import tr_noop


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

    @property
    def is_plugin(self) -> bool:
        """True for a simulator loaded from the plugins folder (E14)."""
        return "plugin" in self.extra

    def create(self, **kwargs):
        plugin = self.extra.get("plugin")
        cls = (plugin.simulator if plugin is not None
               else getattr(importlib.import_module(self.module), self.class_name))
        return cls(self, **kwargs)


SIMULATORS: dict[str, SimulatorInfo] = {
    s.id: s
    for s in [
        SimulatorInfo(
            id="S1",
            title=tr_noop("Cosmology Calculator"),
            tagline=tr_noop("Ages, distances and more for any redshift."),
            description=tr_noop(
                "Choose a cosmological model and a redshift z. The calculator tells you how old the "
                "universe was when the light left the object, how long the light travelled, and the "
                "different 'distances' astronomers use."
            ),
            how_to_use=[
                tr_noop("Pick a model from <b>Preset</b> (Planck 2018 is today's best estimate) or type your own "
                        "values."),
                tr_noop("Enter the <b>redshift z</b> of the object you are interested in."),
                tr_noop("Read the results table. Click any row to see what that quantity means."),
                tr_noop("Use the plots to see how each quantity changes with redshift."),
            ],
            things_to_try=[
                tr_noop("Set z = 1100: this is the cosmic microwave background. How old was the universe?"),
                tr_noop("Compare the comoving and light-travel distances at z = 3. Why is one larger?"),
                tr_noop("Switch to Einstein–de Sitter. Is the universe older or younger than in Planck 2018?"),
            ],
            lessons=["L0.6", "L1.2", "L1.5", "L2.1", "L2.2", "L2.6", "L2.7", "L3.4", "L3.5", "L4.5"],
            module="cosmos.gui.simulators.calculator",
            class_name="CalculatorSimulator",
            icon="∑",
        ),
        SimulatorInfo(
            id="S2",
            title=tr_noop("Expansion History Explorer"),
            tagline=tr_noop("How matter and dark energy shape the past and future."),
            description=tr_noop(
                "Adjust how much matter and dark energy the universe contains and watch the scale "
                "factor a(t) change. The Ωm–ΩΛ map shows which combinations lead to eternal "
                "expansion, a Big Crunch or no Big Bang at all."
            ),
            how_to_use=[
                tr_noop("Move the <b>Ωm</b> and <b>ΩΛ</b> sliders, or click anywhere on the Ωm–ΩΛ map."),
                tr_noop("The upper plot shows the size of the universe over time; today is at t = 0 where a = 1."),
                tr_noop("Press <b>Pin curve</b> to keep the current curve for comparison."),
                tr_noop("Read the summary for the universe's age, geometry and fate."),
            ],
            things_to_try=[
                tr_noop("Find the Big Crunch region: increase Ωm above 1 with ΩΛ = 0."),
                tr_noop("Pin Planck 2018, then set ΩΛ = 0 with Ωm = 0.3. Which universe is older?"),
                tr_noop("Cross the dashed 'accelerating' line and watch the curve's shape today."),
            ],
            lessons=["L2.3", "L2.4", "L2.5", "L2.6", "L3.3", "L3.4", "L3.5"],
            module="cosmos.gui.simulators.expansion",
            class_name="ExpansionSimulator",
            icon="⤴",
        ),
        SimulatorInfo(
            id="S3",
            title=tr_noop("Powers of Ten Zoom"),
            tagline=tr_noop("From a human to the observable universe."),
            description=tr_noop(
                "Zoom out from human size to the whole observable universe, one power of ten at a time. "
                "Every object is drawn to scale for the current field of view."
            ),
            how_to_use=[
                tr_noop("Drag the <b>zoom slider</b> or scroll the mouse wheel over the view."),
                tr_noop("Press <b>Play</b> to fly out automatically; press again to stop."),
                tr_noop("Use <b>Jump to</b> to go straight to an object."),
                tr_noop("The panel on the right describes what is visible and how long light takes to cross the view."),
            ],
            things_to_try=[
                tr_noop("How many powers of ten separate the Earth from the Sun's size?"),
                tr_noop("Find the scale where light needs one year to cross the view."),
                tr_noop("Notice how empty space is between stars compared with between galaxies."),
            ],
            lessons=["L0.1", "L0.2", "L0.7", "L1.4"],
            module="cosmos.gui.simulators.powers_of_ten",
            class_name="PowersOfTenSimulator",
            icon="⊙",
        ),
        SimulatorInfo(
            id="S4",
            title=tr_noop("Spectrum & Redshift Simulator"),
            tagline=tr_noop("See spectral lines shift with motion and expansion."),
            description=tr_noop(
                "Atoms absorb light at precise wavelengths, leaving dark lines in a spectrum. Move the "
                "source or expand the universe and watch the lines slide toward the red (or blue)."
            ),
            how_to_use=[
                tr_noop("Choose <b>Doppler motion</b> (a moving source) or <b>Cosmic expansion</b> (a distant "
                        "galaxy)."),
                tr_noop("Move the slider. The lower strip shows the observed spectrum; the upper one is the laboratory "
                        "spectrum."),
                tr_noop("Lines that leave the visible range continue into the infrared (grey area)."),
                tr_noop("Try the <b>Mystery galaxy</b> challenge to measure a redshift yourself."),
            ],
            things_to_try=[
                tr_noop("At what redshift does the red Hα line leave the visible range?"),
                tr_noop("Make the source approach you: which way do the lines move?"),
                tr_noop("At z = 2, how big was the universe compared with today?"),
            ],
            lessons=["L0.3", "L1.5", "L2.2"],
            module="cosmos.gui.simulators.spectrum",
            class_name="SpectrumSimulator",
            icon="≋",
        ),
        SimulatorInfo(
            id="S5",
            title=tr_noop("Hubble Diagram Fitter"),
            tagline=tr_noop("Measure the expansion rate from real data."),
            description=tr_noop(
                "Plot galaxy velocities against distances and fit a straight line through the origin. "
                "Its slope is the Hubble constant H0, and 1/H0 estimates the age of the universe."
            ),
            how_to_use=[
                tr_noop("Select a <b>data set</b>: Hubble's original 1929 data or a simulated modern sample."),
                tr_noop("Move the <b>H0 slider</b> until the line follows the points; watch the residuals shrink."),
                tr_noop("Press <b>Find best fit</b> to let least squares find the optimal slope."),
                tr_noop("Compare the Hubble time 1/H0 with the true age of the universe (13.8 Gyr)."),
            ],
            things_to_try=[
                tr_noop("Fit Hubble's data. Why is his H0 about seven times too large?"),
                tr_noop("Notice the galaxies with negative velocities in 1929: which ones are they?"),
                tr_noop("Fit the modern sample and compute 1/H0 in billions of years."),
            ],
            lessons=["L0.5", "L1.1", "L1.2"],
            module="cosmos.gui.simulators.hubble_fit",
            class_name="HubbleFitSimulator",
            icon="⟋",
        ),
        SimulatorInfo(
            id="S6",
            title=tr_noop("Galaxy Rotation Curve"),
            tagline=tr_noop("Uncover dark matter from how galaxies spin."),
            description=tr_noop(
                "Stars orbit the centre of a galaxy. If only visible matter pulled on them, distant stars "
                "would move slowly. Build a galaxy from a bulge, a disk and a dark matter halo and compare "
                "with a measured-style rotation curve."
            ),
            how_to_use=[
                tr_noop("Adjust the <b>bulge</b> and <b>disk</b> masses: these are the stars and gas you can see."),
                tr_noop("Turn the <b>dark matter halo</b> on and change its mass."),
                tr_noop("Compare the total curve with the data points."),
                tr_noop("Press <b>Fit halo to data</b> to find the halo mass that matches best."),
            ],
            things_to_try=[
                tr_noop("Pick a real galaxy from the <b>Galaxy</b> list: 138 measured curves from the SPARC survey."),
                tr_noop("Compare a dwarf (DDO154) with a giant spiral (UGC02885): which needs proportionally more "
                        "dark matter?"),
                tr_noop("Switch off the halo: how does the curve behave in the outskirts?"),
                tr_noop("How much dark matter lies inside 30 kpc compared with visible matter?"),
                tr_noop("Can you fit the data with a heavier disk and no halo? Why not?"),
                tr_noop("Tick <b>Use MOND</b>: can modified gravity explain the curve without dark matter?"),
            ],
            lessons=["L3.2", "L6.7"],
            module="cosmos.gui.simulators.rotation_curve",
            class_name="RotationCurveSimulator",
            icon="◎",
        ),
        SimulatorInfo(
            id="S7",
            title=tr_noop("Balloon & Raisin-Bread Expansion"),
            tagline=tr_noop("Why every galaxy sees all others moving away."),
            description=tr_noop(
                "Galaxies sit on a grid that stretches as the universe expands. Pick any galaxy as your "
                "home: all others recede from it, faster the farther they are. Light travelling between "
                "galaxies is stretched too."
            ),
            how_to_use=[
                tr_noop("Press <b>Play</b> to expand the universe; <b>Reset</b> returns to the start."),
                tr_noop("<b>Click a galaxy</b> to stand on it. Arrows show how others move as seen from there."),
                tr_noop("Press <b>Emit light</b> to send a wave and watch its wavelength stretch."),
                tr_noop("Toggle the comoving grid to see that galaxies keep their grid positions."),
            ],
            things_to_try=[
                tr_noop("Choose a galaxy at the edge. Is the pattern of arrows any different?"),
                tr_noop("Compare an arrow twice as long with the distance: is the ratio the same?"),
                tr_noop("Emit light, wait until the scale factor doubles, and read the redshift."),
            ],
            lessons=["L1.3", "L2.1", "L2.2"],
            module="cosmos.gui.simulators.balloon",
            class_name="BalloonSimulator",
            icon="◌",
        ),
        SimulatorInfo(
            id="S12",
            title=tr_noop("CMB Power Spectrum Explorer"),
            tagline=tr_noop("How the universe's ingredients shape the CMB peaks."),
            description=tr_noop(
                "The pattern of hot and cold spots in the cosmic microwave background encodes the geometry and "
                "contents of the universe. Change ordinary matter, dark matter, curvature and the initial "
                "fluctuations, and watch the acoustic peaks and the simulated sky respond."
            ),
            how_to_use=[
                tr_noop("Move a slider in <b>Contents of the universe</b>; the blue curve is your universe, the dashed "
                        "curve the Planck 2018 model."),
                tr_noop("Read the <b>peak positions</b> and the acoustic angle in the results panel."),
                tr_noop("Open the <b>What the sky looks like</b> tab to compare simulated sky patches."),
                tr_noop("Press <b>Reset to Planck 2018</b> to start again."),
            ],
            things_to_try=[
                tr_noop("Make space closed (Ωk = −0.1): do the spots on the sky look larger or smaller?"),
                tr_noop("Double Ωb h². Which peaks grow and which shrink?"),
                tr_noop("Set τ = 0.15. Which part of the spectrum is suppressed?"),
            ],
            lessons=["L5.1", "L5.7", "L4.4", "L3.2", "L2.5"],
            module="cosmos.gui.simulators.cmb_spectrum",
            class_name="CMBSpectrumSimulator",
            icon="∿",
        ),
        SimulatorInfo(
            id="S13",
            title=tr_noop("2D N-body Structure Formation"),
            tagline=tr_noop("Watch gravity build the cosmic web from tiny ripples."),
            description=tr_noop(
                "Tens of thousands of dark matter particles start almost uniformly spread, with tiny ripples. "
                "Gravity amplifies the ripples into sheets, filaments and halos that merge into ever larger "
                "structures. Compare the growth with linear theory and try warm dark matter."
            ),
            how_to_use=[
                tr_noop("Press <b>Play</b>. Time is measured by the growth factor D; D = 1 corresponds to today."),
                tr_noop("Watch the lower plot: at first the density contrast follows linear theory, then gravity takes "
                        "over."),
                tr_noop("Change the <b>spectral index</b> or choose <b>warm dark matter</b>, then press <b>Apply and "
                        "restart</b>."),
                tr_noop("A different <b>random seed</b> gives a different universe with the same statistics."),
            ],
            things_to_try=[
                tr_noop("When does the simulation first deviate from the linear-theory line?"),
                tr_noop("Compare n = −2 with n = 0: which one forms large filaments, which one many small clumps?"),
                tr_noop("Run the same seed with warm dark matter. What happens to the smallest halos?"),
            ],
            lessons=["L5.3", "L5.4", "L5.5", "L1.4", "L4.7", "L7.4"],
            module="cosmos.gui.simulators.nbody_sim",
            class_name="NBodySimulator",
            icon="⁂",
        ),
        SimulatorInfo(
            id="S14",
            title=tr_noop("Gravitational Lensing Simulator"),
            tagline=tr_noop("Bend light with galaxies, clusters and black holes."),
            description=tr_noop(
                "Mass bends the paths of light rays. Put a point mass, a galaxy or a galaxy cluster in front of "
                "distant galaxies and see multiple images, arcs and Einstein rings. The Einstein radius uses real "
                "cosmological distances, so the ring's size weighs the lens."
            ),
            how_to_use=[
                tr_noop("Choose a <b>lens type</b> and set its mass or velocity dispersion."),
                tr_noop("<b>Drag</b> inside the image to move the background galaxy; the orange cross marks its true "
                        "position."),
                tr_noop("Change the <b>lens and source redshifts</b> and watch the Einstein radius in the "
                        "measurements."),
                tr_noop("Switch to <b>a field of galaxies</b> to see how a cluster distorts many galaxies at once."),
            ],
            things_to_try=[
                tr_noop("Place the source exactly behind the lens: what shape appears?"),
                tr_noop("Tick <b>Switch the lens off</b> to see the sky as it would look without gravity."),
                tr_noop("Keep the lens mass fixed and move the lens redshift: where is lensing strongest?"),
            ],
            lessons=["L5.6", "L3.2", "L0.4"],
            module="cosmos.gui.simulators.lensing_sim",
            class_name="LensingSimulator",
            icon="⊚",
        ),
        SimulatorInfo(
            id="S8",
            title=tr_noop("Curvature Visualizer"),
            tagline=tr_noop("Triangles, circles and rulers in curved space."),
            description=tr_noop(
                "Space itself can be curved. Draw the same triangle and circle in closed (spherical), flat and "
                "open (hyperbolic) space and see how angles, circumferences and apparent sizes change. Then "
                "connect the curvature radius to our own universe."
            ),
            how_to_use=[
                tr_noop("Change the <b>triangle side</b>: small triangles look flat everywhere, large ones reveal "
                        "curvature."),
                tr_noop("Read the angle sums and circumference ratios in <b>Measurements</b>."),
                tr_noop("Open the <b>Apparent sizes</b> tab to see why curvature changes the size of CMB spots."),
                tr_noop("Set <b>Ωk</b> to see how big the curvature radius of our universe could be."),
            ],
            things_to_try=[
                tr_noop("Make a spherical triangle whose angles add up to 270°. What fraction of the sphere does it "
                        "cover?"),
                tr_noop("At which radius does a circle on a sphere have the largest circumference?"),
                tr_noop("With |Ωk| = 0.002, how many observable-universe radii fit into the curvature radius?"),
            ],
            lessons=["L6.1", "L2.5"],
            module="cosmos.gui.simulators.curvature",
            class_name="CurvatureSimulator",
            icon="△",
        ),
        SimulatorInfo(
            id="S9",
            title=tr_noop("Spacetime & Horizon Diagram"),
            tagline=tr_noop("Light cones, horizons and galaxy worldlines through cosmic time."),
            description=tr_noop(
                "A spacetime diagram shows distance across and time upwards. Follow the paths of light and "
                "galaxies, see the teardrop-shaped past light cone, and watch the particle horizon, event horizon "
                "and Hubble sphere evolve. Switch to conformal coordinates where light moves at 45°."
            ),
            how_to_use=[
                tr_noop("Choose a universe with the <b>preset</b> or the Ωm and ΩΛ sliders."),
                tr_noop("Pick <b>coordinates</b>: proper distance, comoving distance, or comoving distance with "
                        "conformal time."),
                tr_noop("Move the <b>scale factor of the observer</b> to watch from the past or the future."),
                tr_noop("Toggle light cones, horizons and worldlines to focus on one idea at a time."),
            ],
            things_to_try=[
                tr_noop("In proper coordinates, where is the past light cone widest? Where does it cross the Hubble "
                        "sphere?"),
                tr_noop("Switch to conformal time: why do light cones become straight lines?"),
                tr_noop("Remove dark energy (ΩΛ = 0). What happens to the event horizon?"),
            ],
            lessons=["L6.1", "L2.6"],
            module="cosmos.gui.simulators.spacetime",
            class_name="SpacetimeSimulator",
            icon="⧖",
        ),
        SimulatorInfo(
            id="S15",
            title=tr_noop("Inflation Slow-Roll Simulator"),
            tagline=tr_noop("Roll a field down a potential and test its predictions."),
            description=tr_noop(
                "During inflation a scalar field rolled slowly down its potential, driving exponential expansion "
                "and creating the seeds of all structure. Choose a potential, watch the field roll, and compare its "
                "predicted spectral index and gravitational waves with Planck and BICEP/Keck."
            ),
            how_to_use=[
                tr_noop("Choose a <b>model</b>; some have an extra parameter."),
                tr_noop("Set <b>N*</b>, how many e-folds before the end the observed scales left the horizon."),
                tr_noop("Press <b>Play</b> to watch the field roll and inflation end when ε reaches 1."),
                tr_noop("Check whether the star for your model lies inside the green allowed region of the nₛ–r plot."),
            ],
            things_to_try=[
                tr_noop("Why is the simplest φ² model ruled out even though its nₛ looks fine?"),
                tr_noop("Change the decay constant of natural inflation: can you make it consistent?"),
                tr_noop("How many e-folds of inflation does the comoving Hubble radius plot need to explain the "
                        "horizon?"),
            ],
            lessons=["L6.3"],
            module="cosmos.gui.simulators.inflation_sim",
            class_name="InflationSimulator",
            icon="⥥",
        ),
        SimulatorInfo(
            id="S16",
            title=tr_noop("Supernova Ia Discovery"),
            tagline=tr_noop("Repeat the 1998 discovery and meet the Hubble tension."),
            description=tr_noop(
                "Fit the brightness of Type Ia supernovae against redshift to find out whether the expansion is "
                "slowing down or speeding up. Then calibrate the supernova brightness in two different ways and see "
                "how the Hubble constant changes."
            ),
            how_to_use=[
                tr_noop("Choose a sample: two simulated ones, or the real <b>Pantheon+</b> compilation."),
                tr_noop("Compare the data with the empty, matter-only and best-fit models in the <b>Hubble "
                        "diagram</b>."),
                tr_noop("Open the <b>Ωm–ΩΛ plane</b> to see which universes the data allow; try <b>Assume a flat "
                        "universe</b>."),
                tr_noop("Switch the <b>calibration</b> and read the Hubble constant."),
            ],
            things_to_try=[
                tr_noop("Fit the real Pantheon+ sample. Where does the best fit land, and how many sigma is the "
                        "evidence for acceleration?"),
                tr_noop("With the 1998-like sample, how strong is the evidence for acceleration with and without "
                        "flatness?"),
                tr_noop("Do distant supernovae look brighter or fainter than in an empty universe?"),
                tr_noop("Which calibration gives a Hubble constant close to Planck, and which close to SH0ES?"),
            ],
            lessons=["L6.6", "L3.3", "L1.1", "L7.6"],
            module="cosmos.gui.simulators.supernova_sim",
            class_name="SupernovaSimulator",
            icon="✶",
        ),
        SimulatorInfo(
            id="S18",
            title=tr_noop("Build Your Own Universe"),
            tagline=tr_noop("Design a universe and grade it against observations."),
            description=tr_noop(
                "Choose every ingredient: the expansion rate, ordinary and dark matter, curvature, radiation, "
                "neutrinos and evolving dark energy. See its history, contents, fate and CMB spectrum, and get a "
                "report card that compares it with real measurements."
            ),
            how_to_use=[
                tr_noop("Start from a <b>preset</b> or move any slider."),
                tr_noop("Read the <b>score</b> at the top and open the <b>Report card</b> to see which tests pass."),
                tr_noop("Use <b>History and contents</b> to see when radiation, matter and dark energy dominated."),
                tr_noop("Try evolving or phantom dark energy with <b>w0</b> and <b>wa</b>."),
            ],
            things_to_try=[
                tr_noop("Build a universe without dark matter that still passes the age test. Which tests fail?"),
                tr_noop("Set w0 = −1.3: when does the Big Rip happen?"),
                tr_noop("Can you find a universe very different from ΛCDM that passes every test?"),
            ],
            lessons=["L6.2", "L6.7", "L6.8", "L4.7"],
            module="cosmos.gui.simulators.sandbox",
            class_name="SandboxSimulator",
            icon="✦",
        ),
        SimulatorInfo(
            id="S10",
            title=tr_noop("Interactive Cosmic Timeline"),
            tagline=tr_noop("From the Planck era to the far future on one slider."),
            description=tr_noop(
                "Slide through 60 orders of magnitude of cosmic time. At every moment the timeline shows the "
                "temperature, the typical particle energy, the density, the size of the observable universe and "
                "what dominated the energy budget, together with the epoch you are in and how well we know it."
            ),
            how_to_use=[
                tr_noop("Drag the <b>time slider</b>; it is logarithmic, so each step of 1 is a factor of ten in "
                        "time."),
                tr_noop("Or pick an epoch from <b>Jump to an epoch</b>, or press <b>Play history</b>."),
                tr_noop("Read <b>The universe at this moment</b> for temperature, energy, density and horizon size."),
                tr_noop("The coloured bands show how confident we are: red speculative, yellow theory, blue tested in "
                        "laboratories, green directly observed."),
            ],
            things_to_try=[
                tr_noop("Find the moment when the universe was as hot as the core of the Sun. Which epoch is it?"),
                tr_noop("When did matter overtake radiation, and dark energy overtake matter?"),
                tr_noop("How large was the observable universe at the end of nucleosynthesis?"),
                tr_noop("Go 100 billion years into the future. What happens to the temperature?"),
            ],
            lessons=["L4.1", "L4.2", "L4.5", "L6.4"],
            module="cosmos.gui.simulators.cosmic_timeline",
            class_name="CosmicTimelineSimulator",
            icon="⧗",
        ),
        SimulatorInfo(
            id="S11",
            title=tr_noop("BBN Abundance Explorer"),
            tagline=tr_noop("How the first three minutes made hydrogen, helium and lithium."),
            description=tr_noop(
                "Big Bang nucleosynthesis predicts how much helium, deuterium, helium-3 and lithium formed in the "
                "first minutes, depending on the density of ordinary matter. Change the baryon density, add extra "
                "neutrino species or change the neutron lifetime, and compare the predictions with the observed "
                "abundances and with the CMB."
            ),
            how_to_use=[
                tr_noop("Move <b>η₁₀</b>, the number of baryons per ten billion photons. The vertical line marks your "
                        "value."),
                tr_noop("The coloured horizontal bands are the observed abundances; the green vertical band is the "
                        "baryon density measured from the CMB."),
                tr_noop("Use <b>Change the physics</b> to add extra relativistic species or change the neutron "
                        "lifetime."),
                tr_noop("The right-hand panel shows neutrons decaying while the universe waits for deuterium to "
                        "survive."),
            ],
            things_to_try=[
                tr_noop("Press <b>From deuterium</b>. Does the result land inside the CMB band?"),
                tr_noop("Find the lithium minimum. Can any baryon density fit lithium and deuterium together?"),
                tr_noop("Set ΔN_eff = 1. How much does helium change, and could the observations allow it?"),
                tr_noop("Lengthen the neutron lifetime to 888 s, the beam-experiment value. What happens to helium?"),
            ],
            lessons=["L4.3", "L4.2", "L4.5"],
            module="cosmos.gui.simulators.bbn_explorer",
            class_name="BBNExplorerSimulator",
            icon="⚛",
        ),
        SimulatorInfo(
            id="S17",
            title=tr_noop("Olbers' Paradox Simulator"),
            tagline=tr_noop("Why is the night sky dark?"),
            description=tr_noop(
                "Look at a patch of sky in a universe full of stars. If the universe were infinite, static and "
                "eternal, every line of sight would end on a star and the sky would blaze. Switch on a finite age, "
                "stellar lifetimes or expansion and watch the sky go dark."
            ),
            how_to_use=[
                tr_noop("Start with <b>Olbers' universe</b>: the patch is completely covered by stars."),
                tr_noop("Tick <b>The universe has a finite age</b> and shorten the light-travel distance."),
                tr_noop("Try <b>Stars shine for a limited time</b> and <b>The universe expands</b> as well."),
                tr_noop("Compare the plots: the brightness curve and the shell argument show why each change works."),
            ],
            things_to_try=[
                tr_noop("Keep an infinite age but lower the star density. Does the sky ever get dark?"),
                tr_noop("Which is more effective in our universe, the finite age or redshift dimming? (Read "
                        "<b>Our universe</b>.)"),
                tr_noop("Find the light-travel distance at which half of the sky is covered."),
            ],
            lessons=["L0.6"],
            module="cosmos.gui.simulators.olbers_sim",
            class_name="OlbersSimulator",
            icon="✧",
        ),
        SimulatorInfo(
            id="S19",
            title=tr_noop("Likelihood & MCMC Explorer"),
            tagline=tr_noop("Watch a measurement being made, one step at a time."),
            description=tr_noop(
                "Every number in cosmology comes from three pieces: a model, a likelihood that says how well "
                "it fits the data, and a way to explore the parameters. Here a random walker explores Ωm and "
                "ΩΛ against real supernovae, and the cloud it leaves behind is the measurement."
            ),
            how_to_use=[
                tr_noop("Press <b>Run the chain</b>, then <b>Watch it walk</b> to see the walker leave its starting "
                        "corner and settle into the good region."),
                tr_noop("Read the mean and the ± in <b>What the chain says</b>: that is the measurement."),
                tr_noop("Change the <b>proposal step σ</b> and watch the acceptance rate and the shape of the cloud."),
                tr_noop("Press <b>Run 4 chains</b> to check R̂: four walkers from four corners must agree."),
            ],
            things_to_try=[
                tr_noop("Set σ = 0.005. The acceptance rate goes above 90% — why is the answer still wrong?"),
                tr_noop("Set σ = 0.4. Almost nothing is accepted; what happens to the effective sample size?"),
                tr_noop("Tick <b>Assume a flat universe</b>: one parameter instead of two, and a much tighter Ωm."),
                tr_noop("Compare the 1998-like sample with Pantheon+: the same method, twenty-five years of data."),
            ],
            lessons=["L7.2", "L7.3", "L7.1", "L3.3", "L6.6"],
            module="cosmos.gui.simulators.mcmc_sim",
            class_name="MCMCSimulator",
            icon="⛓",
        ),
        SimulatorInfo(
            id="S20",
            title=tr_noop("Distance Ladder Builder"),
            tagline=tr_noop("Climb from parallax to H0 and follow every error bar."),
            description=tr_noop(
                "The local Hubble constant rests on three rungs: parallaxes calibrate Cepheids, Cepheids "
                "calibrate type Ia supernovae, and distant supernovae measure the expansion. Design the "
                "observing programme, watch the uncertainty of each rung flow into H0, and see why a "
                "systematic error survives any amount of data. The measurements are simulated."
            ),
            how_to_use=[
                tr_noop("Choose an <b>observing programme</b>, or set the numbers of stars and supernovae yourself."),
                tr_noop("Read <b>The three rungs</b>: each panel is one step of the ladder with its own fit."),
                tr_noop("Open <b>Error budget</b> to see how much each rung contributes to the uncertainty of H0."),
                tr_noop("Press <b>Repeat 300×</b> to check the error bar by rerunning the whole measurement."),
                tr_noop("Add a <b>systematic</b> — a parallax zero-point offset or crowding — and compare the shift "
                        "with the error bar."),
            ],
            things_to_try=[
                tr_noop("Start from the Key Project preset. Which rung limits it, and what does fixing only that "
                        "rung achieve?"),
                tr_noop("Add 2000 Hubble-flow supernovae. Why does the total error barely move?"),
                tr_noop("Set a parallax offset of +20 µas: how many σ does the toy H0 move, and would you notice?"),
                tr_noop("Set the true H0 to 67.4. How precise must the ladder be to rule out 73 at 5σ?"),
            ],
            lessons=["L7.3", "L7.6", "L1.1", "L6.6"],
            module="cosmos.gui.simulators.ladder_sim",
            class_name="LadderSimulator",
            icon="🪜",
        ),
        SimulatorInfo(
            id="S21",
            title=tr_noop("Survey Designer"),
            tagline=tr_noop("Choose area, depth and time, and see the error bars you would get."),
            description=tr_noop(
                "A redshift survey measures the expansion history through the baryon acoustic oscillation "
                "scale. Pick a tracer, a redshift range, a sky area and an amount of telescope time, and the "
                "forecast shows how precisely each redshift slice would be measured — and whether the survey "
                "is limited by its volume, by too few galaxies, or by systematic errors."
            ),
            how_to_use=[
                tr_noop("Start from a <b>programme</b> such as BOSS, DESI or Euclid, or build your own."),
                tr_noop("Change the <b>tracer</b>, the redshift range and the <b>target density</b>, and watch n̄P."),
                tr_noop("Set the <b>sky area</b> and the <b>telescope time</b>; if the spectra run out, the density "
                        "is diluted."),
                tr_noop("Open <b>Wide or deep?</b> to see the best area for the galaxies you can afford."),
                tr_noop("Add a <b>systematic floor</b> to see when more data stops helping."),
            ],
            things_to_try=[
                tr_noop("Compare the BOSS and DESI programmes: what gives DESI its factor of two?"),
                tr_noop("Choose quasars. Why does doubling their density help more than doubling the area?"),
                tr_noop("Keep the number of galaxies fixed and find the area where the error is smallest."),
                tr_noop("With a 0.3% systematic floor, how many years are worth observing?"),
            ],
            lessons=["L7.4", "L7.6", "L5.2"],
            module="cosmos.gui.simulators.survey_sim",
            class_name="SurveySimulator",
            icon="🗺",
        ),
        SimulatorInfo(
            id="S22",
            title=tr_noop("Standard Siren Explorer"),
            tagline=tr_noop("Measure H₀ from a gravitational-wave merger."),
            description=tr_noop(
                "A merging pair of neutron stars or black holes gives its own distance away: relativity "
                "fixes the amplitude of the wave, so the strain that arrives here is a distance with no "
                "calibration behind it. Add the redshift of the host galaxy and you have H₀ without a "
                "single rung of the distance ladder — if you can find the host, and if you can tell how "
                "the binary was tilted."
            ),
            how_to_use=[
                tr_noop("Start from <b>GW170817</b>, the one merger so far whose host galaxy was identified."),
                tr_noop("Watch the <b>chirp</b>: its rising frequency gives the masses, its amplitude the "
                        "distance."),
                tr_noop("Open <b>Distance vs inclination</b> to see why the distance error is so lopsided."),
                tr_noop("Change the <b>detector network</b>: sensitivity sets the reach, the number of sites "
                        "sets the sky area."),
                tr_noop("Turn off <b>the host galaxy is known</b> to make it a dark siren and watch the "
                        "candidates multiply."),
                tr_noop("Raise the <b>number of events</b> until the error crosses the 2% line."),
            ],
            things_to_try=[
                tr_noop("Reproduce GW170817: 40 Mpc, SNR 32, H₀ to about 15%. Which error dominates?"),
                tr_noop("Move the same merger to 400 Mpc. What happens first — the SNR or the host?"),
                tr_noop("Compare a face-on and an edge-on binary at the same distance. Which is measured better?"),
                tr_noop("How many bright sirens does it take to beat the Hubble tension at 2%?"),
                tr_noop("Switch to the Einstein Telescope. How far can a neutron-star merger be heard?"),
            ],
            lessons=["L6.5", "L6.9", "L6.6", "L1.2"],
            module="cosmos.gui.simulators.siren_sim",
            class_name="SirenSimulator",
            icon="〰",
        ),
        SimulatorInfo(
            id="S23",
            title=tr_noop("Redshift Survey Slice"),
            tagline=tr_noop("Build a cone diagram and find the cosmic web in it."),
            description=tr_noop(
                "A mock catalogue: a simulated universe, observed the way a telescope would observe it. "
                "Galaxies are sampled from a density field grown from random initial conditions, then placed "
                "at the distance their redshift implies. Switch the observing effects on one at a time and "
                "watch what each of them does to the map — and to the clustering measured from it."
            ),
            how_to_use=[
                tr_noop("Start from a <b>survey</b>: CfA2 and SDSS are the real slices, <b>the true universe</b> "
                        "has no observing effects at all."),
                tr_noop("Read the <b>cone diagram</b>: we are at the point, distance grows outwards, and the "
                        "filaments and voids are the cosmic web."),
                tr_noop("Open <b>Truth vs observed</b> to see the same galaxies with and without their motions."),
                tr_noop("Raise the <b>cluster velocity dispersion</b> until the fingers of God are unmistakable."),
                tr_noop("Set an <b>apparent magnitude limit</b> and watch the <b>Selection</b> tab: the far edge "
                        "empties out because of the telescope, not the universe."),
                tr_noop("Change the <b>random seed</b>: a different universe, the same statistics."),
            ],
            things_to_try=[
                tr_noop("Compare the true universe with the observed one. Which structures move, and which way?"),
                tr_noop("Turn the peculiar velocities off but keep the cluster dispersion. What is left?"),
                tr_noop("Raise the redshift error to 0.02. How much of the cosmic web survives?"),
                tr_noop("In the correlation function, find the scale below which the mock has no structure."),
                tr_noop("Raise the bias to 2.5. The galaxies clump harder — does ξ change shape or only height?"),
            ],
            lessons=["L7.5", "L1.4", "L5.4", "L7.4"],
            module="cosmos.gui.simulators.slice_sim",
            class_name="SliceSimulator",
            icon="🕸",
        ),
        SimulatorInfo(
            id="S24",
            title=tr_noop("CMB Sky Viewer"),
            tagline=tr_noop("The real microwave sky, with the mask and the filters."),
            description=tr_noop(
                "This is not a model. It is the WMAP nine-year map of the whole sky: the oldest light "
                "there is, released 380 000 years after the Big Bang, with the ripples that every "
                "galaxy grew from. Apply the analysis mask the team published, blur the map or keep "
                "only its fine detail, and measure what is left — the size of the spots, how alike "
                "two points are, and whether the distribution is the Gaussian inflation predicts."
            ),
            how_to_use=[
                tr_noop("Turn the <b>KQ85 mask</b> off and on. The bright band is our own galaxy, not "
                        "the early universe."),
                tr_noop("Raise <b>Smooth by</b> and watch the rms fall in the summary."),
                tr_noop("Tick <b>keep only what is smaller</b> to subtract the blur and leave the "
                        "degree-scale spots."),
                tr_noop("Open <b>Correlation function</b> and read the spot size off the half-way point."),
                tr_noop("Switch the <b>projection</b> between Mollweide and longitude–latitude."),
            ],
            things_to_try=[
                tr_noop("With the mask off, how much larger are the extremes? Whose light is that?"),
                tr_noop("Smooth by 5°. How much of the 67 µK is left, and what has been thrown away?"),
                tr_noop("In <b>How much survives blurring</b>, find the scale where the curve bends."),
                tr_noop("Compare the histogram with the Gaussian. Inflation predicts that shape."),
                tr_noop("Find the coldest spot. It is a real feature, and it has its own literature."),
            ],
            lessons=["L5.1", "L4.4", "L5.7", "L1.5"],
            module="cosmos.gui.simulators.sky_sim",
            class_name="SkySimulator",
            icon="🌌",
        ),
        SimulatorInfo(
            id="S25",
            title=tr_noop("Recombination Explorer"),
            tagline=tr_noop("Why the universe became transparent at 3000 K, not 158 000 K."),
            description=tr_noop(
                "380 000 years after the Big Bang the free electrons were captured by protons, and light "
                "could suddenly travel for ever: that light is the cosmic microwave background. Follow the "
                "number of free electrons as the universe cools, compare the naive equilibrium answer with "
                "the real one, and see where the CMB photons scattered for the last time."
            ),
            how_to_use=[
                tr_noop("Read <b>Free electrons</b>: the solid curve is the real history, the dashed one the "
                        "Saha equilibrium it lags behind."),
                tr_noop("Open <b>The last-scattering surface</b> to see where the photons we receive today "
                        "were last deflected, and how thick that shell is."),
                tr_noop("Open <b>Why so cold?</b> to count the photons that can still ionise an atom."),
                tr_noop("Change the <b>baryon density</b> or today's <b>CMB temperature</b> and watch "
                        "the moment of transparency move."),
            ],
            things_to_try=[
                tr_noop("At what temperature is half of the hydrogen neutral? Compare it with 13.6 eV."),
                tr_noop("How much later than Saha does the real recombination happen, and why?"),
                tr_noop("Switch to the logarithmic axis. How many electrons never find a proton?"),
                tr_noop("Double today's CMB temperature. Does last scattering happen at a different "
                        "temperature, or only at a different redshift?"),
                tr_noop("Lower Ωb h² to 0.01. What happens to the electrons left over?"),
            ],
            lessons=["L4.4", "L1.5", "L5.1", "L4.2"],
            module="cosmos.gui.simulators.recombination_sim",
            class_name="RecombinationSimulator",
            icon="⚛",
        ),
        SimulatorInfo(
            id="S26",
            title=tr_noop("The Far Future"),
            tagline=tr_noop("Heat death, Big Rip or Big Crunch: how the universe ends."),
            description=tr_noop(
                "Run the universe forward. Choose what the dark energy does and follow the expansion for "
                "hundreds of billions of years, then along a timeline that reaches 10¹⁰⁰ years: the last "
                "stars, evaporating galaxies and black holes. If the dark energy is phantom, watch the Big "
                "Rip take apart clusters, galaxies, the Solar System and finally atoms."
            ),
            how_to_use=[
                tr_noop("Pick a <b>universe</b>, or move the sliders to make your own."),
                tr_noop("<b>Expansion</b> shows the size of the universe from today onwards; a dashed line "
                        "marks the end, if there is one."),
                tr_noop("<b>The next 10¹⁰⁰ years</b> puts the milestones on a logarithmic axis. Faded ones "
                        "never happen in this universe."),
                tr_noop("<b>Big Rip countdown</b> shows when each bound system is torn apart."),
                tr_noop("<b>Galaxies we can still reach</b> counts the galaxies a message sent at each "
                        "moment could ever arrive at."),
            ],
            things_to_try=[
                tr_noop("In our universe, what fraction of the galaxies we can see could we still reach today?"),
                tr_noop("Choose w = −1.5. How long before the Big Rip does the Earth explode?"),
                tr_noop("Bring w from −1.5 towards −1. How fast does the Big Rip recede?"),
                tr_noop("Give dark energy a negative value. When does the Big Crunch come?"),
                tr_noop("Switch dark energy off. Which milestones stop happening, and why?"),
            ],
            lessons=["L6.10", "L3.3", "L2.6", "L6.9"],
            module="cosmos.gui.simulators.future_sim",
            class_name="FutureSimulator",
            icon="⌛",
        ),
        SimulatorInfo(
            id="S27",
            title=tr_noop("Halo Mass Function Explorer"),
            tagline=tr_noop("How many haloes of each mass, when — and why clusters weigh σ8."),
            description=tr_noop(
                "Every galaxy lives in a halo of dark matter, and the halo mass function says how many haloes "
                "of each mass there are. It follows from the ripples in the early universe alone: a region "
                "collapses once its overdensity passes a threshold. Go back in time to the first star-forming "
                "haloes, or count the giant clusters on today's sky and see how steeply they depend on σ8."
            ),
            how_to_use=[
                tr_noop("Move <b>σ8</b> and <b>Ωm</b>; the dashed curves stay at Planck 2018 for comparison."),
                tr_noop("<b>Mass function</b> shows how many haloes there are of each mass at the chosen "
                        "<b>redshift</b>."),
                tr_noop("<b>Clusters on the sky</b> counts every halo above the <b>threshold</b> out to z = 1, "
                        "for several values of σ8."),
                tr_noop("<b>Rare peaks</b> shows σ(M): a halo forms where it crosses δc = 1.686."),
                tr_noop("<b>Across cosmic time</b> follows small haloes, galaxies and clusters from z = 20 "
                        "to today."),
            ],
            things_to_try=[
                tr_noop("Raise σ8 by 10%. How much do the clusters above 10¹⁵ M☉/h change?"),
                tr_noop("Lower the threshold to 10¹³ M☉/h and repeat. Is the effect smaller?"),
                tr_noop("Go to z = 20. How many haloes can make the first stars?"),
                tr_noop("Find the redshift at which the typical collapsing halo was the size of the Milky Way."),
                tr_noop("Switch between Press–Schechter and Sheth–Tormen. Where do they disagree most?"),
            ],
            lessons=["L4.8", "L5.5", "L6.6", "L5.4"],
            module="cosmos.gui.simulators.halo_sim",
            class_name="HaloSimulator",
            icon="⬤",
        ),
        SimulatorInfo(
            id="S28",
            title=tr_noop("21-cm Global Signal Explorer"),
            tagline=tr_noop("Listen to hydrogen from the dark ages and the first stars."),
            description=tr_noop(
                "Neutral hydrogen absorbs and emits at 21 cm, and that line, stretched by the expansion, "
                "arrives today at radio frequencies between about 10 and 200 MHz. Averaged over the whole "
                "sky it records the history of the gas: cooling in the dark ages, the first starlight, the "
                "first X-ray heating and reionisation. Change the astrophysics and compare with the "
                "contested EDGES detection."
            ),
            how_to_use=[
                tr_noop("<b>The global signal</b> shows the brightness temperature against frequency; the "
                        "top axis gives the redshift."),
                tr_noop("Move <b>Lyman-α coupling</b> to change when the first stars light up, and <b>X-ray "
                        "heating</b> to change when and how much the gas is warmed."),
                tr_noop("<b>Three temperatures</b> shows why: absorption wherever the spin temperature is "
                        "below the background."),
                tr_noop("<b>What couples the spins</b> shows collisions giving way to starlight."),
                tr_noop("Add an <b>extra radio background</b> to try to reach the depth EDGES reported."),
            ],
            things_to_try=[
                tr_noop("Where is the dark-ages trough, and why can it not be seen from the ground?"),
                tr_noop("Switch the X-ray heating off. What happens to the emission?"),
                tr_noop("Make the first stars form later. Which way does the trough move in frequency?"),
                tr_noop("How big a radio background does it take to match EDGES?"),
                tr_noop("Delay reionisation to z = 6. What changes at the high-frequency end?"),
            ],
            lessons=["L6.4", "L4.8"],
            module="cosmos.gui.simulators.global21_sim",
            class_name="Global21Simulator",
            icon="📡",
        ),
        SimulatorInfo(
            id="S29",
            title=tr_noop("Dark Matter Detection"),
            tagline=tr_noop("Build an underground detector and draw your own exclusion curve."),
            description=tr_noop(
                "If dark matter is made of WIMPs, a few of them should bounce off atomic nuclei in a detector "
                "deep underground. Choose the target, the size, the threshold and the background of your "
                "detector, pick a WIMP, and see the recoil spectrum it would leave, the events of a single "
                "run, the yearly modulation — and the exclusion curve a null result would draw."
            ),
            how_to_use=[
                tr_noop("Start from an <b>experiment</b>, or change the target, exposure, threshold and "
                        "background yourself."),
                tr_noop("Set the <b>WIMP mass</b> and <b>cross-section</b>. The summary says how many events "
                        "it would give and whether it would be discovered, excluded or hidden."),
                tr_noop("<b>Exclusion curve</b>: everything above your curve would have been seen. Your WIMP "
                        "is the round dot."),
                tr_noop("<b>A simulated run</b> draws one random outcome; press <b>Run the experiment again</b> "
                        "for another."),
                tr_noop("<b>Annual modulation</b> shows the few-per-cent yearly swing as the Earth orbits the Sun."),
            ],
            things_to_try=[
                tr_noop("With the xenon detector, at what WIMP mass is the limit strongest? Why does it weaken on "
                        "both sides?"),
                tr_noop("Set the WIMP mass to 5 GeV. Which detector can still see it?"),
                tr_noop("Double the exposure with no background. How much lower does the curve go? Now add "
                        "20 background events."),
                tr_noop("Find a WIMP that is excluded but would not have been discovered."),
                tr_noop("Run the same experiment several times. How much does the number of events jump?"),
            ],
            lessons=["L3.6", "L3.2", "L6.8"],
            module="cosmos.gui.simulators.detection_sim",
            class_name="DetectionSimulator",
            icon="⛏",
        ),
    ]
}

# Keep simulators in numerical order regardless of when they were added. Plugins
# use P-numbers and sort after every built-in S-number (E14).
def _order(item) -> tuple[int, int]:
    key = item[0]
    return (0 if key.startswith("S") else 1, int(key[1:]))


SIMULATORS = dict(sorted(SIMULATORS.items(), key=_order))
BUILTIN_IDS = frozenset(SIMULATORS)


def register_plugins(plugins) -> list[str]:
    """Add plugin simulators to the catalogue. Returns the ids that were added."""
    from cosmos.plugins import to_info

    added = []
    for plugin in plugins:
        if plugin.id in SIMULATORS:
            continue
        SIMULATORS[plugin.id] = to_info(plugin)
        added.append(plugin.id)
    if added:
        ordered = sorted(SIMULATORS.items(), key=_order)
        SIMULATORS.clear()
        SIMULATORS.update(ordered)
    return added


def forget_plugins() -> None:
    """Drop every plugin simulator. Used by the tests."""
    for key in [k for k in SIMULATORS if k not in BUILTIN_IDS]:
        del SIMULATORS[key]
