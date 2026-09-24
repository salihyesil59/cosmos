# Changelog

All notable changes to Cosmos are recorded here. Versions follow
[semantic versioning](https://semver.org): until 1.0 the interface and the save
format may still change between releases.

## Unreleased

### Added

- **A Spanish interface** (Español), complete: all 2073 strings, the same coverage
  as the Turkish pack — the chrome, the Guide panel, the guided tour, the quiz, the
  badges, the challenges and every simulator with its controls, tooltips and
  results. Choose it in **View → Language**.
- **[TRANSLATING.md](TRANSLATING.md)**, a guide for translators: what is translated
  and what stays English, the three commands that start and compile a language, the
  six rules that matter (placeholders, HTML, `&` accelerators, shortcuts, numbers,
  Markdown), the terminology the existing packs settled on, and how to check the
  result before sending it in.

### Changed

- The README's translation claim and `tools/content_stats.py` now count every
  bundled pack rather than the Turkish one alone.

## 0.2.0 — 2026-09-24

Phase 4 (see [ROADMAP.md](https://github.com/salihyesil59/cosmos/blob/main/ROADMAP.md)): the course grows to 58 lessons and 29
simulators — recombination, the far future, the first stars, dark matter searches,
galaxy formation and how to read a paper — and gains the tools that make studying
a habit: flashcards, a daily goal and streak, "Remember this" cards, backups, and
a website edition of the whole course.

Progress from 0.1.0 carries over unchanged: open the new version and everything
you had is still there. One worked problem changed its id (see *Fixed*).

### Added

- **L6.10 The Far Future**: heat death, Big Rip or Big Crunch — the exponential
  expansion, the milestones to 10¹⁰⁰ years and the Big Rip countdown, with a quiz,
  teacher notes, three glossary terms and two formulas
- **S25 Recombination Explorer**: the Saha equation against Peebles' three-level
  atom, the visibility function and the optical depth, and why the universe became
  transparent at 3000 K rather than 158 000 K; the last-scattering peak lands at
  z ≈ 1080, within 1% of RECFAST
- **S26 The Far Future**: the expansion from today onwards for any Ωm, ΩΛ and w, a
  timeline of the far future, the Big Rip countdown of Caldwell, Kamionkowski &
  Weinberg (2003) and the galaxies a signal sent today could still reach
- **Back up and restore progress** from the File menu: everything learned, the
  notes, the bookmarks and the review deck in one file. A restore keeps this
  computer's theme, language and text size, and a file that is not a backup
  changes nothing
- **L4.8 The Dark Ages and Cosmic Dawn**: how the gas cooled after recombination,
  the first haloes, why gas must cool to make a star, Population III, and what
  JWST found above z = 10
- **S27 Halo Mass Function Explorer**: Press–Schechter and Sheth–Tormen from the
  Eisenstein–Hu spectrum, the clusters on the whole sky out to z = 1 and how
  steeply they depend on σ8, rare peaks, and haloes across cosmic time from z = 20
  — the first atomic-cooling haloes reach one per (Mpc/h)³ at z ≈ 13
- **L3.6 Hunting Dark Matter**: what any candidate must explain, the WIMP
  miracle, direct detection and the neutrino fog, DAMA's modulation, indirect
  searches and the LHC, and axion haloscopes
- **S29 Dark Matter Detection**: WIMP recoil spectra on xenon, argon, germanium and
  silicon (Standard Halo Model, Helm form factor), Poisson exclusion curves — the
  xenon preset reaches 3 × 10⁻⁴⁸ cm² near 50 GeV, close to LZ's published 2024
  limit — a simulated run and the annual modulation
- **L5.8 Galaxy Formation**: cooling against collapse, discs from tidal spin,
  the stellar-to-halo mass relation (with a new lesson figure) and supernova and
  black-hole feedback
- **S28 21-cm Global Signal Explorer**: the gas temperature solved from
  recombination onwards, collisional and Lyman-α coupling, X-ray heating and
  reionisation — a dark-ages trough of −40 mK at 16 MHz and a cosmic-dawn trough
  near −185 mK at 67 MHz — compared with EDGES, with an optional excess radio
  background
- **Fourteen new worked problems** for the Phase 4 lessons and simulators: WIMP
  recoils, axion frequencies, the dark-ages gas, the 21-cm line, virial
  temperatures, disc sizes, peak heights, the Big Rip and black-hole evaporation
- **Glossary flashcards**: add a term from the glossary, or all the terms of a
  lesson with one button; they come back on the Review page on the same 1-3-7-16-35
  day schedule as missed quiz questions. Space turns a card over, 1 and 2 say
  whether you knew it. A new badge, *Words of the trade*, for ten terms learned
- **A study streak and a daily goal** on the home page. Quiz questions, reviews,
  flashcards, problem attempts and solved challenges each count as a step; the goal
  (none, 5, 10, 20 or 40 a day) is the learner's choice, and one day off does not
  break the streak. A new badge, *A week in a row*
- **Remember this**: each lesson's closing summary is now a highlighted card, and
  *Learn → "Remember this" sheet* and *File → Print the "Remember this" sheet*
  collect the cards of every completed lesson (or the whole course, before the
  first is completed)
- **L7.7 Reading a Cosmology Paper**: the anatomy of a paper, reading in three
  passes, what "±", "95% upper limit", "tension" and "evidence" claim, parameter
  tables, triangle plots, and six questions to ask before believing a surprise —
  with a quiz, teacher notes, three glossary terms and a worked problem on S₈
- **The course as a website**: *File → Export the course as a website*, or
  `python tools/build_site.py`, writes a reading edition — every lesson with its
  formulas, figures, "Remember this" card and a working quiz, the glossary, the
  formula sheet, the worked problems with answer checking, and a catalogue of the
  simulators — as about 60 plain HTML pages that work offline from any folder.
  Every push to main builds it as a CI artifact
- **A style check in CI**: ruff (pycodestyle, pyflakes, bugbear, pyupgrade; rules
  in `ruff.toml`) runs on every push, and packages are only built when it passes.
  Getting there removed unused imports, renamed ambiguous and unused loop
  variables, and wrapped the 57 lines longer than 120 characters without changing
  a single translatable string
- **The README's numbers are checked**: `tools/content_stats.py` counts the
  content, a test fails when the README falls behind, and `--write` fixes it
- Fifteen guided challenges for the five new simulators; the Turkish pack is
  complete at 2073 strings

### Fixed

- Fifteen one-line `:::try` boxes written this round were followed by a stray
  `:::`, and seven older ones had wrapped onto a second line; both showed up as
  text in the lesson. A content test now renders every lesson and fails on any
  leftover marker. The try-box link also no longer says "Open the The Far Future"

- Two worked problems shared the id `p6-schwarzschild`, so solving one marked
  both, and the test that recomputes every answer silently checked only one. The
  M87* problem is now `p6-m87-horizon`, and a test keeps ids unique

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.2.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.2.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.2.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |
| Any browser | `Cosmos-0.2.0-website.zip` — the reading edition: unzip and open `index.html` |

Nothing needs to be installed: each package contains its own Python and Qt, and
every build runs `--selftest` before it is published.

## 0.1.0 — 2026-09-23

The first packaged release: the whole course, complete and self-contained.

### The course

- **53 lessons in 8 levels**, from the scale of the universe to the open problems
  at the frontier — each with objectives, a summary and a quiz
- **Two ways to read every lesson**: *Intuitive* tells the story in words, *With
  the maths* shows every formula and derivation
- **287 quiz questions** with explanations, **51 worked problems** in eight sets,
  and **spaced repetition** that brings back the questions you got wrong
- **184-term glossary**, **66 formulas** with every symbol named, a **history of
  cosmology** with 33 milestones and 18 scientist cards

### The simulators

- **24 simulators**, from the Cosmology Calculator and the Hubble Diagram Fitter
  to the Likelihood & MCMC Explorer, the Distance Ladder Builder and the Standard
  Siren Explorer
- **41 guided challenges** inside them, with hints and automatic checking
- Real data where it matters: the **Pantheon+** supernovae, the **SPARC** rotation
  curves, the **WMAP** nine-year sky map and an **SDSS DR18** galaxy slice.
  Everything the app generates itself is labelled as simulated, in the interface
  and in the exported CSV

### The application

- **Turkish and English** interface; the course text itself is in English
- **Accessibility**: a high-contrast theme, text scaling, focus rings and
  keyboard-only navigation
- **Print anything** as a PDF: one lesson, one level or the whole course
- **Classroom mode**: a progress report a teacher can read, and teacher notes for
  every lesson
- **Your own simulators**: drop a Python file in the plugins folder and it appears
  in the simulator list
- An optional, opt-in **update check** that asks GitHub for the latest release
  number and sends nothing at all
- Starts in under a second, and keeps your progress in a single JSON file you own
- Released under the **MIT licence**; the bundled observational data keeps the
  terms of the teams who measured it

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.1.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.1.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.1.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |

Nothing needs to be installed: each package contains its own Python and Qt. Every
build runs `--selftest` before it is published, which opens every kind of page
off-screen and fails if anything is missing.
