# Cosmos

An interactive desktop application that teaches cosmology, from the size of the
universe and the nature of light to the Friedmann equations, dark energy, the first
minutes after the Big Bang, the growth of cosmic structure, inflation and the open
problems at the frontier of research.

Everything happens in the graphical interface: lessons with formulas and figures,
hands-on simulators, quizzes with explained answers, a glossary and a progress
map. A **Guide** panel explains every page, and a guided tour introduces the app
on first launch.

## Features

- **47 lessons in 8 levels**: Foundations, Observational Cosmology, The Expanding
  Universe, Contents of the Universe, Thermal History, CMB & Structure Formation,
  Advanced Topics, How Cosmologists Work
- **20 simulators**
  - Cosmology Calculator: ages, distances, horizons and recession velocities at any redshift
  - Expansion History Explorer: a(t) and the Ωm–ΩΛ map
  - Powers of Ten Zoom: from a human to the observable universe
  - Spectrum & Redshift Simulator, with a "mystery galaxy" challenge
  - Hubble Diagram Fitter: Hubble's 1929 data and a simulated modern sample
  - Galaxy Rotation Curve: 138 real SPARC galaxies, dark matter halo or MOND
  - Balloon & Raisin-Bread Expansion: expansion with no centre
  - Curvature Visualizer: triangles and circles in closed, flat and open space
  - Spacetime & Horizon Diagram: light cones and horizons in three coordinate systems
  - Interactive Cosmic Timeline: 60 orders of magnitude of cosmic history on one slider
  - BBN Abundance Explorer: the light elements made in the first three minutes
  - Olbers' Paradox Simulator: why the night sky is dark
  - CMB Power Spectrum Explorer: acoustic peaks and simulated sky patches
  - 2D N-body Structure Formation: gravity builds the cosmic web
  - Gravitational Lensing Simulator: arcs, multiple images and Einstein rings
  - Inflation Slow-Roll Simulator: potentials, nₛ and r against Planck and BICEP/Keck
  - Supernova Ia Discovery: fit the real Pantheon+ supernovae and meet the Hubble tension
  - Build Your Own Universe: design a cosmology (neutrino mass included) and grade it against observations
  - Likelihood & MCMC Explorer: watch a measurement being made, combine probes, derive parameters
  - Distance Ladder Builder: parallax → Cepheids → supernovae, with the error budget of H0
- **Two ways to read every lesson**: *Intuitive* tells the story in words,
  *With the maths* shows every formula and derivation
- **242 quiz questions** with explanations; score 70% or more to complete a
  lesson
- **26 guided challenges** inside the simulators, with hints and automatic checking
- **A history of cosmology**: 33 milestones from Copernicus to DESI and 18
  scientist cards, each linked to the lesson that explains the physics
- **40 worked problems** in eight sets, one per level: type a number and the app
  checks it, spots a wrong power of ten or sign, and offers hints and a worked
  solution
- **19 badges** earned by learning: finishing levels, perfect quizzes, exploring
  simulators, solving their challenges and working through the problem sets
- **159-term glossary**: terms in lessons open their definitions in the Guide panel
- **Reference page**: a 57-entry formula sheet, physical constants, a unit
  converter and the parameters of every model
- **Global search** (Ctrl+F) across lesson text, glossary, simulators, formulas and problems
- **Notes and bookmarks**: a private notebook for every page, exportable as Markdown
- Tooltips and **?** buttons on every control
- Progress tracking with a prerequisite map
- Dark and light themes; the interface is translatable and ships with a full Turkish pack
- An optional **Tutor** panel that answers questions with your own API key
- Export plots as PNG/SVG and data as CSV
- Presets: Planck 2018, WMAP 9-year, evolving and phantom dark energy, Einstein–de Sitter and more
- A physics engine verified against [astropy](https://www.astropy.org/), and an
  optional [CAMB](https://camb.readthedocs.io) engine for exact CMB spectra

See [ROADMAP.md](ROADMAP.md) for what is planned next.

## Getting started

Requires Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python main.py
```

You can also start the app with `python -m cosmos`.

## Optional: the Tutor

A **Tutor** panel (F3) can answer questions about the page you are reading. It is
switched off until you paste your own Anthropic API key into it, and nothing
leaves the computer until you press **Ask**. The key is kept only on this machine,
and only if you tick *Remember*; `ANTHROPIC_API_KEY` is picked up automatically if
it is set. Tick *Include the page I am reading* to let the tutor see that lesson
or simulator, or untick it to send only your question. Answers come from a
language model and can be wrong: the lessons, not the tutor, are the course.

## Optional: exact CMB spectra with CAMB

The CMB Power Spectrum Explorer (S12) ships with a fast analytic teaching model.
Install the optional package `camb` and the simulator offers a second engine
that solves the Boltzmann equations properly:

```bash
pip install camb
```

Pick **CAMB — exact Boltzmann code** in the simulator's *How the spectrum is
computed* box. Each update then takes about half a second, and results are
cached. Without `camb` the app behaves exactly as before.

## Interface languages

The course content is English. The interface — menus, buttons, page headings,
badges and the panels around the content — is translatable, and **Turkish ships
with the app**: choose it in **View → Language** and restart. Nearly 1200 strings
are translated: the Guide panel, the guided tour, the quiz, the challenges and
every simulator — its controls, its tooltips and the results it reports back.
The course itself — lesson text, quiz questions, the glossary and the formula
sheet — stays in English, as do the names of datasets, epochs and galaxies.

To add another language, use the standard Qt tools:

```bash
python tools/update_translations.py --language de   # writes cosmos/i18n/cosmos_de.ts
pyside6-linguist cosmos/i18n/cosmos_de.ts           # translate it
python tools/update_translations.py --release       # compiles cosmos_de.qm
```

The language then appears in **View → Language** and is used the next time
Cosmos starts. Without a compiled `.qm` file the app is English, as before.

## A standalone Windows executable

No Python installation is needed to run a packaged build.

```bash
pip install -r requirements-dev.txt
python tools/build_exe.py            # one file:  dist/Cosmos.exe   (~100 MB)
python tools/build_exe.py --onedir   # a folder:  dist/Cosmos/Cosmos.exe (starts in under a second)
python tools/build_exe.py --zip      # also writes dist/Cosmos-<version>-windows.zip
```

The build bundles the whole course (lessons, quizzes, glossary, formulas,
challenges, history and the observational data) and leaves the test-only
dependencies out. When it finishes, the script runs the packaged program with
`--selftest`, which opens every kind of page off-screen and fails the build if
anything is missing:

```bash
dist\Cosmos.exe --selftest report.txt    # exit code 0 means the build is complete
dist\Cosmos.exe --version
```

The single-file build unpacks itself on every start (about five seconds); the
`--onedir` build starts immediately and is the better choice for daily use.
Progress, notes and bookmarks are stored per user in
`%APPDATA%\Cosmos\progress.json`, so they survive updating the executable.
The application icon is drawn by `tools/make_icon.py`.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

The tests check the physics against astropy, validate all course content (links,
quizzes, formulas) and open every page and simulator headlessly.

GitHub Actions runs the same suite on Windows and Linux for every push and pull
request (`.github/workflows/ci.yml`). Pushes to `main` then build `Cosmos.exe`,
run its self-test and keep it for 14 days as a downloadable artifact of the run.

### Project layout

```
cosmos/
  physics/      GUI-independent cosmology engine (numpy, scipy)
  content/      lessons (Markdown); quizzes, glossary, formulas, challenges and
                history (YAML); curriculum
  achievements.py  badge definitions, computed from the learner's progress
  data/         bundled observational data
  gui/
    pages/      home, lesson, simulators, glossary, reference, search, notes, progress
    simulators/ one module per simulator + registry with guidance texts
    rendering/  Markdown → Qt rich text, mathtext formulas, lesson figures
    widgets/    Guide panel, tour, quiz, prerequisite map, plots, controls
  progress.py   learner progress, notes and bookmarks (JSON in the user's app-data folder)
tests/
```

### Writing lessons

Lessons are Markdown files in `cosmos/content/lessons/` with YAML front matter.
On top of standard Markdown they support:

| Syntax | Result |
|---|---|
| `$$ ... $$` / `$ ... $` | display / inline formula (matplotlib mathtext) |
| `[[key]]` or `[[key\|text]]` | link to a glossary term |
| `:::note Title` … `:::` | callout (`note`, `tip`, `key`, `warning`, `history`, `example`, `math`) |
| `:::try S1 Text` | "Try it" box that opens a simulator |
| `{{figure:name}}` | figure drawn from the physics engine |
| `[text](lesson:L1.2)` | link to another lesson |

Add the lesson id to `cosmos/content/curriculum.yaml` and its quiz to
`cosmos/content/quizzes/`. Entries for the formula sheet live in
`cosmos/content/formulas.yaml`, simulator challenges in `challenges.yaml`, worked
problems in `problems.yaml` and
the timeline in `history.yaml`. A `:::math` callout marks a derivation, which
the intuitive lesson view hides. Run `pytest` to check the new content.

## Data sources

- Scolnic et al. (2022) and Brout et al. (2022), the **Pantheon+** supernova
  compilation, with the SH0ES calibration of Riess et al. (2022) — bundled in
  `cosmos/data/external/` and used by the Supernova Ia Discovery simulator
- Lelli, McGaugh & Schombert (2016), the **SPARC** rotation curves of 175 disk
  galaxies — bundled in `cosmos/data/external/` and used by the Galaxy Rotation
  Curve simulator
- Planck Collaboration (2020), *Planck 2018 results. VI. Cosmological parameters*
- Hinshaw et al. (2013), *Nine-year WMAP observations: cosmological parameter results*
- Hubble, E. (1929), *A relation between distance and radial velocity among
  extra-galactic nebulae*, PNAS 15, 168
- Fixsen, D. J. (2009), *The temperature of the cosmic microwave background*
- Riess et al. (2022, SH0ES), Freedman et al. (2019, CCHP), Wong et al. (2020, H0LiCOW),
  Aiola et al. (2020, ACT) and Abbott et al. (2017, GW170817) for the Hubble constant figure
- Heymans et al. (2021, KiDS-1000) and DES Collaboration (2022, Year 3) for S8
- BICEP/Keck Collaboration (2021) for the limit on primordial gravitational waves
- Eisenstein & Hu (1998) transfer function; Hu & Sugiyama (1996) decoupling redshift
- Steigman (2007, 2012) fitting formulas for the primordial abundances; Cooke et al. (2018)
  for the observed deuterium abundance

Two data sets are real measurements, redistributed unmodified with their
provenance in [cosmos/data/external/README.md](cosmos/data/external/README.md):
the Pantheon+ supernovae and the SPARC rotation curves. Everything else the app
plots — the "simulated modern sample", the simulated supernova samples, the
illustrative rotation curve, the 2D N-body universe, the star fields of the
Olbers simulator and the CMB and 21-cm teaching models — is generated by the app
and labelled as such in the interface.
