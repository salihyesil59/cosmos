# Changelog

All notable changes to Cosmos are recorded here. Versions follow
[semantic versioning](https://semver.org): until 1.0 the interface and the save
format may still change between releases.

## Unreleased

The first round of Phase 4 (see [ROADMAP.md](ROADMAP.md)).

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
- Six guided challenges for the two new simulators; the Turkish pack is complete
  at 1851 strings

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
