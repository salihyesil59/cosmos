# Cosmos — Roadmap

Cosmos is a desktop application (Python + PySide6) that teaches cosmology step by
step: from the very basics (scales, light, gravity) to advanced research topics
(inflation, CMB physics, structure formation). Every lesson is paired with
interactive simulators, guidance and quizzes.

The project grows in phases. **Phase 1** built the core application, **Phase 2**
worked through the backlog and **Phase 3** added the craft of cosmology, real data
and the packaged releases; all three are finished. **Phase 4** at the end of this
file collects what comes next.

Legend: `[x]` done · `[ ]` planned

---

## Technical decisions

| Layer              | Choice                                                         |
|--------------------|----------------------------------------------------------------|
| GUI                | PySide6 (Qt 6)                                                 |
| Plots              | matplotlib embedded in Qt; custom `QPainter` widgets for animations |
| Formulas           | matplotlib mathtext (rendered to images inside lesson pages)   |
| Physics engine     | numpy + scipy (pure Python package, GUI independent)           |
| Verification       | astropy (tests only)                                           |
| Content            | Markdown lessons + YAML quizzes/glossary, separate from code   |
| Storage            | JSON file in the user's application-data folder                |

---

## Phase 1 — Core application

**Status:** completed on 2026-09-15.

### Curriculum

**Level 0 — Foundations**
- [x] `L0.1` Scales of the Universe
- [x] `L0.2` Distance units: AU, light-year, parsec, megaparsec
- [x] `L0.3` Light, spectra, the Doppler effect and redshift
- [x] `L0.4` Gravity, intuitively: from Newton to Einstein

**Level 1 — Observational Cosmology**
- [x] `L1.1` The cosmic distance ladder
- [x] `L1.2` The Hubble–Lemaître law
- [x] `L1.3` The cosmological principle

**Level 2 — The Expanding Universe**
- [x] `L2.1` The scale factor; comoving vs. proper distance
- [x] `L2.2` Cosmological redshift vs. Doppler redshift
- [x] `L2.3` The Friedmann equations (Newtonian derivation)
- [x] `L2.4` Critical density and density parameters
- [x] `L2.5` The geometry of space: open, flat, closed

**Level 3 — Contents of the Universe**
- [x] `L3.1` Radiation, matter, dark energy and the equation of state
- [x] `L3.2` Evidence for dark matter
- [x] `L3.3` Dark energy and the accelerating universe
- [x] `L3.4` The ΛCDM model

**Level 4 — Thermal History**
- [x] `L4.1` A timeline of the universe
- [x] `L4.2` Temperature in an expanding universe
- [x] `L4.3` Big Bang nucleosynthesis
- [x] `L4.4` Recombination and the last scattering surface

### Simulators
- [x] `S1` Cosmology Calculator
- [x] `S2` Expansion History Explorer (with the Ωm–ΩΛ plane)
- [x] `S3` Powers of Ten Zoom
- [x] `S4` Spectrum & Redshift Simulator
- [x] `S5` Hubble Diagram Fitter
- [x] `S6` Galaxy Rotation Curve
- [x] `S7` Balloon / Raisin-Bread Expansion

### Guidance & learning
- [x] `G1` Lesson pages (text, formulas, figures, "Try it" links to simulators)
- [x] `G2` Guided tour on first launch
- [x] `G3` Tooltips and "?" info buttons on every control
- [x] `G4` Glossary with clickable terms inside lessons
- [x] `G5` Quizzes with explained answers
- [x] `G6` Progress tracking and prerequisite map

### Extras & quality
- [x] `E1` Bundled offline data (Planck 2018, WMAP9, Hubble 1929)
- [x] `E2` Export plots (PNG/SVG) and results (CSV)
- [x] `E3` Dark / light theme
- [x] `E4` Cosmology presets (Planck18, WMAP9, Einstein–de Sitter, …)
- [x] `E5` Physics engine unit tests against astropy

---

## Backlog — added over time

### Curriculum

**Level 0 — Foundations**
- [x] `L0.5` A history of cosmology: from geocentrism to the Big Bang
- [x] `L0.6` Olbers' paradox: why is the night sky dark?

**Level 1 — Observational Cosmology**
- [x] `L1.4` Galaxies, clusters and the cosmic web
- [x] `L1.5` The discovery of the cosmic microwave background

**Level 2 — The Expanding Universe**
- [x] `L2.6` Horizons: particle horizon, Hubble sphere, event horizon
- [x] `L2.7` Distance measures: luminosity distance, angular diameter distance, lookback time

**Level 3 — Contents of the Universe**
- [x] `L3.5` Computing the age of the universe

**Level 4 — Thermal History**
- [x] `L4.5` Neutrino decoupling and the cosmic neutrino background
- [x] `L4.6` Baryogenesis: the matter–antimatter asymmetry

**Level 5 — CMB & Structure Formation**
- [x] `L5.1` CMB anisotropies, the power spectrum and acoustic peaks
- [x] `L5.2` Baryon acoustic oscillations
- [x] `L5.3` Jeans instability and linear perturbation growth
- [x] `L5.4` The matter power spectrum
- [x] `L5.5` Hierarchical structure formation and N-body simulations
- [x] `L5.6` Gravitational lensing (strong and weak)

**Level 6 — Advanced Topics**
- [x] `L6.1` Minimal general relativity: metrics, geodesics, the FLRW metric
- [x] `L6.2` Deriving the Friedmann equations from Einstein's field equations
- [x] `L6.3` Inflation: horizon/flatness/monopole problems, slow roll, n_s and r
- [x] `L6.4` Reionization and 21-cm cosmology
- [x] `L6.5` Gravitational waves and standard sirens
- [x] `L6.6` Current tensions: the Hubble tension and the S8 tension
- [x] `L6.7` Alternative models: MOND, modified gravity, quintessence
- [x] `L6.8` Open problems: the nature of dark matter and dark energy, quantum gravity, the multiverse

### Simulators
- [x] `S8` Curvature Visualizer (triangles on sphere, plane and saddle)
- [x] `S9` Spacetime / Horizon Diagram (light cones, conformal diagram)
- [x] `S10` Interactive Cosmic Timeline
- [x] `S11` BBN Abundance Explorer
- [x] `S12` CMB Power Spectrum Explorer (approximate model)
- [x] `S13` 2D N-body Structure Formation
- [x] `S14` Gravitational Lensing Simulator
- [x] `S15` Inflation Slow-Roll Simulator
- [x] `S16` Supernova Ia Discovery (re-create the 1998 result)
- [x] `S17` Olbers' Paradox Simulator
- [x] `S18` Build Your Own Universe (sandbox)

### Guidance & learning
- [x] `G7` "Intuitive ↔ Mathematical" view for every lesson
- [x] `G8` Step-by-step challenges inside simulators
- [x] `G9` Formula sheet and constants/units reference
- [x] `G10` Global search across lessons and glossary
- [x] `G11` Notes and bookmarks
- [x] `G12` Historical timeline of discoveries and scientist cards
- [x] `G13` Achievements and badges
- [x] `G14` Turkish for the Guide panel, the tour and the simulator controls
- [x] `G20` Turkish for what the simulators report back: readouts, banners, quiz and challenges

### Extras & quality
- [x] `E1+` Pantheon+ supernova sample and SPARC rotation curves (license check, needs download)
- [x] `E6` Optional CAMB/CLASS integration for exact CMB spectra
- [x] `E7` Standalone Windows `.exe` with PyInstaller
- [x] `E8` Internationalisation (i18n) infrastructure
- [x] `E9` Optional "Ask the Tutor" AI assistant (user-supplied API key)

---

## Phase 3 — What could come next

Everything above is finished: 43 lessons, 18 simulators, the guidance features,
real data, a packaged executable, a Turkish interface and the optional CAMB and
tutor extras. The items below are candidates for the next rounds, written in the
same style. ★ marks the ones worth doing first; ticked items have been added
since (the course now has 53 lessons and 23 simulators).

### Curriculum

**Level 7 — How cosmologists actually work**
- [x] ★ `L7.1` Reading a scientific plot: log axes, error bars, confidence contours
- [x] ★ `L7.2` From data to a parameter: likelihoods, χ², and what "5σ" means
- [x] `L7.3` MCMC in practice: sampling a posterior, degeneracies, convergence
- [x] `L7.4` How a survey is built: DESI, Euclid, Rubin and JWST compared
- [x] `L7.5` Simulations as experiments: from initial conditions to a mock catalogue
- [x] `L7.6` Systematics: the errors that do not shrink with more data

**Additions to existing levels**
- [x] ★ `L4.7` Neutrino mass and cosmology: how the lightest particles weigh the universe
- [x] `L5.7` CMB polarisation and lensing: E-modes, B-modes and what they carry
- [x] `L6.9` Black holes in cosmology: from the first image to primordial black holes
- [x] `L0.7` Orders of magnitude: estimating in your head before you compute

### Simulators
- [x] ★ `S19` Likelihood & MCMC Explorer: fit a model, watch the chain, read the contours
- [x] ★ `S20` Distance Ladder Builder: parallax → Cepheids → supernovae, with error propagation
- [x] `S21` Survey Designer: choose area, depth and time, see the error bars you would get
- [x] `S22` Standard Siren Explorer: measure H0 from a gravitational-wave merger
- [x] `S23` Redshift Survey Slice: build a cone diagram and find the cosmic web in it
- [x] `S24` CMB Sky Viewer: the real WMAP sky, with masking and filtering

### Guidance & learning
- [x] ★ `G15` Worked problem sets: numeric exercises with checked answers, one per level
- [x] `G16` Spaced repetition: bring back quiz questions you got wrong, days later
- [x] `G17` Accessibility pass: font scaling, a high-contrast theme, keyboard-only navigation
- [x] `G18` Export a lesson (or the whole course) as PDF for printing
- [x] `G19` Classroom mode: a progress report a teacher can read, and teacher notes per lesson

### Extras & quality
- [x] ★ `E10` Continuous integration: run the tests and build the executable on every push
- [x] `E11` macOS and Linux packages (.app bundle, AppImage)
- [x] `E12` Faster start: lazy figures and a smaller one-file build
- [x] `E13` Update check for the packaged app (opt-in, no telemetry)
- [x] `E14` A plugin interface so a teacher can add their own simulator without touching the app
- [x] `E15` Real CMB and large-scale-structure data (the WMAP 9-year ILC map, an SDSS DR18 slice) with a licence check

---

## Phase 4 — Next steps

Phase 3 is complete: 53 lessons, 24 simulators, real CMB and galaxy data, packages
for three platforms and a plugin interface. Phase 4 fills the remaining gaps in the
story — how the universe became transparent, how it will end, what dark matter
might be, how the first galaxies formed — and makes the learner's own record
safer and more portable. ★ marks the ones worth doing first; ticked items are done.

### Curriculum

- [x] ★ `L6.10` The far future: heat death, Big Rip or Big Crunch
- [x] `L3.6` Hunting dark matter: WIMPs, axions, sterile neutrinos and the experiments that look for them
- [x] `L4.8` The dark ages and cosmic dawn: the first stars, the first galaxies and what JWST found
- [x] `L5.8` Galaxy formation: gas cooling, feedback and how galaxies live in their haloes
- [x] `L7.7` Reading a cosmology paper: from the abstract to the contour plot

### Simulators

- [x] ★ `S25` Recombination Explorer: Saha against Peebles, the visibility function, and why 3000 K
- [x] ★ `S26` The Far Future: the expansion ahead, a timeline to 10¹⁰⁰ years and the Big Rip countdown
- [x] `S27` Halo Mass Function Explorer: Press–Schechter, how many clusters of each mass, and σ8
- [x] `S28` 21-cm Global Signal Explorer: the absorption trough of cosmic dawn and what shapes it
- [x] `S29` Dark Matter Detection: recoil spectra, backgrounds and how an exclusion curve is drawn

### Guidance & learning

- [x] ★ `G21` Back up and restore progress: everything learned, notes and the review deck in one file
- [x] `G22` Glossary flashcards, scheduled by the same spaced-repetition deck as the quizzes
- [x] `G23` A study streak and a gentle daily goal on the home page
- [x] `G24` "Remember this" cards at the end of every lesson, collected into a printable sheet
- [x] `G25` Worked problems for L6.10 and the two new simulators

### Extras & quality

- [x] `E16` A style check (ruff) in continuous integration
- [x] `E17` A test that keeps the numbers in the README (lessons, simulators, questions) in step with the content
- [x] `E18` A second full interface language (Spanish), with a contributor guide for translators
- [x] `E19` Export the course as a static website that runs in a browser without installing anything

## Phase 5 — Making room

Everything the course needs is now in the app, and that had become the problem:
the Guide panel opened with the window and took nearly half of it, the navigation
list showed 58 lessons and 29 simulators at once, and the toolbar repeated what the
menus and the list already offered. Phase 5 takes nothing away — it decides what is
on screen before you ask for it.

### Interface

- [x] ★ `D1` A calmer window: side panels closed until asked for and never wider
  than a third, one section of the navigation open at a time, a nine-item toolbar,
  a readable text measure, and one set of icons drawn in code instead of emoji
- [x] ★ `D2` A window that stays where you put it, and a test that keeps every page
  inside the smallest window the app offers
- [x] `D3` One icon language everywhere: no emoji left in the interface, and the
  simulators' own symbols drawn through the same pipeline as the rest
- [x] `D4` The simulators sorted into five families, in the navigation list, on the
  simulator page and on the home page
- [x] `D5` A minimum window size the app can actually meet, small enough for a
  1024x768 screen, and a lesson header that carries one thing at a time

---

## Phase 6 — Show your working

The app plots real measurements and data it invents, side by side, and says which
is which at each plot. That promise is only as good as the record behind it, and
until now the record lived in a README the learner never sees. Phase 6 brings it
into the app and carries it out with the data: what came from where, what the app
made up and how, and how the numbers are checked. ★ marks the ones worth doing
first. With `V1` to `V5` done, the app can answer every question a careful
reader has about a number on screen: where the data came from, how it was worked
out, what that leaves out, and how the whole engine is checked.

### Transparency

- [x] ★ `V1` A **Data & methods** page: every bundled measurement with its source,
  citation, terms and what was done to it; every generated data set with the
  recipe that makes it; one record in the source that a test keeps honest
- [x] ★ `V2` Provenance that travels: an exported plot carries a caption saying
  what it shows and whether it is real, and an exported CSV carries a header with
  the source, the model parameters and the app version
- [x] `V3` "How was this computed?" beside a simulator's result: the formula it
  used, the reference it follows, and the approximations it makes
- [x] `V4` The validation report inside the app: what each physics routine is
  checked against, and the size of the worst disagreement
- [x] `V5` One honest number for every figure in the course: a test that no lesson
  figure drawn from generated data can go unlabelled, and none of those labels is
  cut off by the edge of the picture

---

## Phase 7 — Within reach

`G17` called itself an accessibility pass, and it did real work: the text scales,
there is a high-contrast theme, and the app can be driven from the keyboard. What
it did not do is make the app *legible to a screen reader*. Counted rather than
guessed, 577 interactive widgets reach one with no name and no text of their own —
among them 285 sliders, spin boxes and combo boxes that have a perfectly good
label sitting beside them, never associated — and not one of the plot canvases,
which is where the answer usually is. Phase 7 is about the learners who cannot see
the screen, and about the pages that keep them waiting. ★ marks the ones worth
doing first.

### Reach

- [x] ★ `A1` Every control announces itself: names taken from the labels already
  beside them, names for the icon-only buttons, and a test that counts what is
  left
- [x] ★ `A2` A plot a screen reader can read: a name and a description on every
  canvas, read off the finished figure so it says what the curve actually does
  and moves when the controls move
- [ ] `A3` A keyboard-only path through every simulator, with a sensible tab
  order, and a test that walks it
- [ ] `A4` The high-contrast theme checked against a contrast ratio rather than
  by eye

### Quality

- [ ] `A5` The Reference page takes 2.6 seconds to open the first time, which is
  the formula sheet, the constants and every preset's age all computed before
  anything is shown. Nobody should wait that long for a page that is mostly text
