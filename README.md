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

- **58 lessons in 8 levels**: Foundations, Observational Cosmology, The Expanding
  Universe, Contents of the Universe, Thermal History, CMB & Structure Formation,
  Advanced Topics, How Cosmologists Work
- **29 simulators**
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
  - CMB Power Spectrum Explorer: acoustic peaks, E and B modes, and simulated sky patches
  - 2D N-body Structure Formation: gravity builds the cosmic web
  - Gravitational Lensing Simulator: arcs, multiple images and Einstein rings
  - Inflation Slow-Roll Simulator: potentials, nₛ and r against Planck and BICEP/Keck
  - Supernova Ia Discovery: fit the real Pantheon+ supernovae and meet the Hubble tension
  - Build Your Own Universe: design a cosmology (neutrino mass included) and grade it against observations
  - Likelihood & MCMC Explorer: watch a measurement being made, combine probes, derive parameters
  - Distance Ladder Builder: parallax → Cepheids → supernovae, with the error budget of H0
  - Survey Designer: choose area, depth and time, and forecast the BAO error bars
  - Standard Siren Explorer: measure H₀ from a merger, with no distance ladder at all
  - Redshift Survey Slice: build a mock catalogue, then compare it with a real SDSS slice
  - CMB Sky Viewer: the real WMAP sky, with the galactic mask, smoothing and filtering
  - Recombination Explorer: Saha against the real history, and why the CMB was released at 3000 K
  - The Far Future: heat death, Big Crunch or Big Rip, on a timeline that runs to 10¹⁰⁰ years
  - Halo Mass Function Explorer: how many haloes of each mass, from the first stars to today's clusters
  - 21-cm Global Signal Explorer: the dark ages and cosmic dawn in the radio sky, and the EDGES puzzle
  - Dark Matter Detection: build an underground detector and draw your own exclusion curve
- **Two ways to read every lesson**: *Intuitive* tells the story in words,
  *With the maths* shows every formula and derivation
- **317 quiz questions** with explanations; score 70% or more to complete a
  lesson
- **56 guided challenges** inside the simulators, with hints and automatic checking
- **A history of cosmology**: 33 milestones from Copernicus to DESI and 18
  scientist cards, each linked to the lesson that explains the physics
- **66 worked problems** in eight sets, one per level: type a number and the app
  checks it, spots a wrong power of ten or sign, and offers hints and a worked
  solution
- **23 badges** earned by learning: finishing levels, perfect quizzes, exploring
  simulators, solving their challenges and working through the problem sets
- **206-term glossary**: terms in lessons open their definitions in the Guide panel
- **Reference page**: a 76-entry formula sheet, physical constants, a unit
  converter and the parameters of every model
- **Global search** (Ctrl+F) across lesson text, glossary, simulators, formulas and problems
- **Spaced repetition**: every quiz question you get wrong comes back the next day,
  then after 3, 7, 16 and 35 days until you have it for good
- **Glossary flashcards**: add a term from the glossary, or every term of a lesson at
  once, and it comes back as a card on the same schedule until you know it
- **A study streak and a daily goal** on the home page: every question, review,
  flashcard, problem and challenge is a step; one day off does not break the streak
- **Remember this**: every lesson ends with a card of its key points, and the cards of
  the lessons you have completed collect into a sheet you can read or print
- **A website of the course**: *File → Export the course as a website* (or
  `python tools/build_site.py`) writes every lesson, with working quizzes, the glossary,
  the formula sheet and the worked problems as plain web pages that open in any browser,
  offline, with nothing to install
- **Print anything**: one lesson, one level or the whole course as a PDF, with its
  figures, its quiz and an answer key
- **Classroom mode**: a progress report a teacher can read, and teacher notes for
  every lesson — the misconception that always comes up, a discussion question and
  what to demonstrate
- **Your own simulators**: drop a Python file in the plugins folder and it appears in
  the list, no changes to the app
- **Notes and bookmarks**: a private notebook for every page, exportable as Markdown
- **Back up and restore** everything you have learned — progress, notes, bookmarks and the
  review deck — as one file, to keep or to carry to another computer
- Tooltips and **?** buttons on every control
- Progress tracking with a prerequisite map
- **Accessible by design**: dark, light and high-contrast themes, text scaling from 80%
  to 160%, visible keyboard focus, and every command reachable without a mouse
- The interface is translatable and ships with a full Turkish pack
- An optional **Tutor** panel that answers questions with your own API key
- An optional, opt-in **update check** — it asks GitHub for the latest release number
  and sends nothing at all, not even a count
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
with the app**: choose it in **View → Language** and restart. More than 2000 strings
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

## Standalone builds

No Python installation is needed to run a packaged build. Every release carries
one for Windows, macOS and Linux on the
[releases page](https://github.com/salihyesil59/cosmos/releases), and
[CHANGELOG.md](CHANGELOG.md) says what is in each. One command builds for
whichever platform you are on:

```bash
pip install -r requirements-dev.txt
python tools/build_app.py              # Windows: dist/Cosmos.exe   (~100 MB)
                                       # macOS:   dist/Cosmos.app
                                       # Linux:   dist/Cosmos/Cosmos
python tools/build_app.py --onedir     # Windows: a folder instead of one file
python tools/build_app.py --package    # also writes the file you would hand out
```

`--package` produces a zip on Windows and macOS, and on Linux an **AppImage** if
`appimagetool` is on the PATH, or a `.tar.gz` if it is not — both are
self-contained and need nothing installed.

The build bundles the whole course (lessons, quizzes, glossary, formulas,
challenges, history and the observational data) and leaves the test-only
dependencies out. When it finishes, the script runs the packaged program with
`--selftest`, which opens every kind of page off-screen and fails the build if
anything is missing:

```bash
dist\Cosmos.exe --selftest report.txt    # exit code 0 means the build is complete
dist\Cosmos.exe --version
```

The single-file Windows build unpacks itself on every start (about five seconds);
every other form starts in well under a second. Progress, notes and bookmarks are
stored per user — `%APPDATA%\Cosmos` on Windows, `~/Library/Application Support/Cosmos`
on macOS, `~/.local/share/Cosmos` on Linux — so they survive updating the app. The
application icons are drawn by `tools/make_icon.py`.

### Adding your own simulator

Drop one Python file into the `plugins` folder beside `progress.json` and it appears
in the simulator list at the next start. The folder is created on first run with a
README containing a complete example. A plugin is ordinary Python and runs with the
same permissions as Cosmos, so only add files you wrote or trust; a broken one is
reported under **Help → Simulator plugins** and skipped.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check .          # the style check CI runs; the rules are in ruff.toml
```

The tests check the physics against astropy, validate all course content (links,
quizzes, formulas) and open every page and simulator headlessly.

GitHub Actions runs the same suite on Windows and Linux for every push and pull
request (`.github/workflows/ci.yml`). Pushes to `main` then build a package for
Windows, macOS and Linux, run each one's self-test, and keep all three for 14 days
as downloadable artifacts of the run.

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
the intuitive lesson view hides. Run `pytest` to check the new content, and
`python tools/content_stats.py --write` to bring the numbers in this README up to
date — a test fails when they fall behind.

## Data sources

- Scolnic et al. (2022) and Brout et al. (2022), the **Pantheon+** supernova
  compilation, with the SH0ES calibration of Riess et al. (2022) — bundled in
  `cosmos/data/external/` and used by the Supernova Ia Discovery simulator
- Lelli, McGaugh & Schombert (2016), the **SPARC** rotation curves of 175 disk
  galaxies — bundled in `cosmos/data/external/` and used by the Galaxy Rotation
  Curve simulator
- Bennett et al. (2013) and Hinshaw et al. (2013), the **WMAP nine-year ILC map**
  and its KQ85 analysis mask from NASA's LAMBDA archive — resampled onto a
  longitude-latitude grid in `cosmos/data/external/` and used by the CMB Sky Viewer
- Almeida et al. (2023), an **SDSS DR18** equatorial slice of 25 149 galaxies from
  SkyServer — bundled in `cosmos/data/external/` and used by the Redshift Survey Slice
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

Four data sets are real measurements, redistributed with their provenance in
[cosmos/data/external/README.md](cosmos/data/external/README.md): the Pantheon+
supernovae, the SPARC rotation curves, the WMAP sky map and the SDSS slice. Everything else the app
plots — the "simulated modern sample", the simulated supernova samples, the
illustrative rotation curve, the 2D N-body universe, the star fields of the
Olbers simulator and the CMB and 21-cm teaching models — is generated by the app
and labelled as such in the interface.

## Licence

Cosmos is released under the [MIT licence](LICENSE): use it, change it, teach
with it, hand it out. The bundled observational data is the exception — it
belongs to the teams who measured it and carries their own terms, which are
recorded in [cosmos/data/external/README.md](cosmos/data/external/README.md)
along with the papers to cite. That exception is stated in [NOTICE](NOTICE);
keep both files if you redistribute the app.
