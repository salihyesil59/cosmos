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

- **43 lessons in 7 levels**: Foundations, Observational Cosmology, The Expanding
  Universe, Contents of the Universe, Thermal History, CMB & Structure Formation,
  Advanced Topics
- **18 simulators**
  - Cosmology Calculator: ages, distances, horizons and recession velocities at any redshift
  - Expansion History Explorer: a(t) and the Ωm–ΩΛ map
  - Powers of Ten Zoom: from a human to the observable universe
  - Spectrum & Redshift Simulator, with a "mystery galaxy" challenge
  - Hubble Diagram Fitter: Hubble's 1929 data and a simulated modern sample
  - Galaxy Rotation Curve: dark matter halo or MOND
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
  - Supernova Ia Discovery: repeat the 1998 analysis and meet the Hubble tension
  - Build Your Own Universe: design a cosmology and grade it against observations
- **215 quiz questions** with explanations; score 70% or more to complete a
  lesson
- **142-term glossary**: terms in lessons open their definitions in the Guide panel
- Tooltips and **?** buttons on every control
- Progress tracking with a prerequisite map
- Dark and light themes
- Export plots as PNG/SVG and data as CSV
- Presets: Planck 2018, WMAP 9-year, evolving and phantom dark energy, Einstein–de Sitter and more
- A physics engine verified against [astropy](https://www.astropy.org/)

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

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

The tests check the physics against astropy, validate all course content (links,
quizzes, formulas) and open every page and simulator headlessly.

### Project layout

```
cosmos/
  physics/      GUI-independent cosmology engine (numpy, scipy)
  content/      lessons (Markdown), quizzes and glossary (YAML), curriculum
  data/         bundled observational data
  gui/
    pages/      home, lesson, simulators, glossary, progress
    simulators/ one module per simulator + registry with guidance texts
    rendering/  Markdown → Qt rich text, mathtext formulas, lesson figures
    widgets/    Guide panel, tour, quiz, prerequisite map, plots, controls
  progress.py   learner progress (saved as JSON in the user's app-data folder)
tests/
```

### Writing lessons

Lessons are Markdown files in `cosmos/content/lessons/` with YAML front matter.
On top of standard Markdown they support:

| Syntax | Result |
|---|---|
| `$$ ... $$` / `$ ... $` | display / inline formula (matplotlib mathtext) |
| `[[key]]` or `[[key\|text]]` | link to a glossary term |
| `:::note Title` … `:::` | callout (`note`, `tip`, `key`, `warning`, `history`, `example`) |
| `:::try S1 Text` | "Try it" box that opens a simulator |
| `{{figure:name}}` | figure drawn from the physics engine |
| `[text](lesson:L1.2)` | link to another lesson |

Add the lesson id to `cosmos/content/curriculum.yaml` and its quiz to
`cosmos/content/quizzes/`. Run `pytest` to check the new content.

## Data sources

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

The "simulated modern sample", the simulated supernova samples, the rotation-curve
data points, the 2D N-body universe, the simulated star fields of the Olbers
simulator and the CMB and 21-cm teaching models are generated by the app and
labelled as such in the interface.
