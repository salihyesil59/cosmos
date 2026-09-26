# Changelog

All notable changes to Cosmos are recorded here. Versions follow
[semantic versioning](https://semver.org): until 1.0 the interface and the save
format may still change between releases.

## Unreleased

### Added

- **Every control in the app now announces itself** (`A1`). `G17` called itself an
  accessibility pass and did real work — scalable text, a high-contrast theme,
  keyboard navigation — but it left the app illegible to a screen reader. Counted
  rather than guessed, 577 interactive widgets reached one as an unnamed "slider"
  or "button": 285 of them sliders, spin boxes and combo boxes with a perfectly
  good label sitting beside them that nothing had ever associated. Four shared
  widgets fixed almost all of it. A `ParameterSlider` now names its slider and its
  spin box after its own label, and passes its tooltip on as a description; a
  labelled row names the control inside it; an info button announces what it is
  about instead of "question mark"; and a search box takes its name from the
  placeholder, which is the only thing that ever said what the box was for and
  which vanishes the moment you type.
- **A focus ring on the plots** (`A3`). `A2` made every canvas focusable so a
  screen reader could reach it, which left a sighted keyboard user tabbing onto a
  plot with nothing to show for it. A canvas paints its own pixels and would cover
  any border of its own, so the frame around it wears the ring instead — reserved
  whether or not it is showing, so nothing shifts when focus arrives.
- **The keyboard path is now checked rather than assumed** (`A3`). All 609
  controls across the 29 simulators turned out to be reachable by Tab already, and
  the order already runs down the page and reaches a plot only after the controls
  that drive it. That is Qt's creation order doing the right thing because the
  pages are built top down — worth a test rather than a shrug, so that the day
  somebody builds a panel out of order, something says so.

- **Every plot can be read out loud** (`A2`). A canvas is where the answer
  usually is, and to a screen reader it was a blank rectangle. All sixty-odd of
  them now carry a description — the axes and their ranges, then each labelled
  series with how many points it has and which way it goes: *"Rotation curve of a
  spiral galaxy. Horizontal axis Distance from the centre (kpc), 0 to 32. Vertical
  axis Orbital speed (km/s), 0 to 350. 3 series: Bulge, rises to about 147 near
  0.52, then falls to 36; …"*
- **The description is read off the figure, not written by hand** (`A2`). That is
  what makes it cover every plot at once, follow the sliders as they move, and
  stay true without anybody keeping it in step — there is nothing to keep in step,
  because it is a reading of the picture that was actually drawn. It knows a peak
  from a trough, twenty scattered measurements from a curve that rises, a
  logarithmic axis, an image, a bar chart, and an unlabelled axis it should not
  announce as "vertical".
- **A canvas can be reached by keyboard** (`A2`). Qt would not give one focus, so
  the description would never have been read out at all.

- **Markup is no longer read aloud** (`A1`). Labels in this app carry `<b>`,
  `<sub>` and `<br>` because they are drawn, not spoken. `strip_markup` turns
  `Ω<sub>b</sub> h<sup>2</sup>` into something a voice can say.
- **A sweep that counts what is left** (`A1`). `tests/test_accessibility.py` walks
  every page, every lesson and every simulator and fails on any control with
  neither a name nor visible text. Qt's own furniture — scroll bars, the clear
  button inside a line edit, a table's corner button — is excluded by name, so the
  sweep cannot flatter itself about its coverage. It found the Guide panel's close
  button on the way in, and it plants a nameless button of its own to prove it
  would still notice.

## 0.6.0 — 2026-09-26

Everything in this release is about being able to trust what is on screen. The app
could already teach the physics; it could not tell you where a number came from,
how it was worked out, what that calculation leaves out, or how the engine behind
it is checked. It can now answer all four, in the interface rather than in a
document nobody using the app ever sees. The interface also lost its last emoji,
and the widths it measures are finally the widths it draws.

### Added

- **A "Data & methods" page, under Reference** (`V1`). The app has always said, at
  each plot, whether it was showing a measurement or something it had generated.
  What it could not do was answer the next question: where did this come from, and
  what was done to it? The new page answers it for all of them — the six bundled
  files of real measurements with their archive, retrieval date, papers to cite
  and terms, what was changed to make them usable offline and what the app
  deliberately does *not* claim with them, followed by the nine kinds of data the
  app invents, each with the recipe and the module that runs it. Every entry links
  to the simulators and lesson figures that use it. Reachable from Help → Data &
  methods, or at the route `reference:data`.
- **Every simulator now says how it works out its answer** (`V3`). Move a slider,
  read a number — and until now there was no way to tell a textbook formula from a
  fit, or an exact calculation from a teaching model good to fifteen per cent. A
  **How this is computed** link beside each simulator opens the Guide at a note
  answering the three questions a careful reader would ask: what is being
  computed, whose method it follows, and what it leaves out. The formulas it names
  are typeset from the formula sheet, so the equation is there rather than
  described.
- **All twenty-nine of them, and a test that keeps it that way** (`V3`). Every
  simulator that ships has a note; every formula it cites has to exist on the
  formula sheet; every note has to list what it leaves out, because all of them
  approximate something. Twenty-four cite a paper — the five that do not are the
  ones with no paper behind them, like the powers-of-ten zoom, which is
  arithmetic. The note is formula-sheet material, so like the formula sheet and
  the glossary it stays in English; the headings around it are translated.

- **The engine's report card, with numbers instead of a claim** (`V4`). The Data
  & methods page used to say the physics was checked against astropy and against
  published values, which a reader had to take on trust. It now shows the table:
  eighteen checks, each with the quantity, what it was compared against, the
  largest disagreement found anywhere in the range tested, and the most that would
  be accepted before the test suite fails. The comparisons with astropy agree to
  about one part in 10^14 — far inside the limits the tests set — and the two
  universes that can be solved with a pen come out exact.
- **Checks of three different kinds** (`V4`). Ten against astropy, four against
  closed forms, four against published measurements. The split is the point, and a
  test enforces it: if astropy and this engine ever shared a mistake, only the
  mathematics and the published numbers would notice.
- **The numbers travel with the app** (`V4`). astropy is a development dependency
  and is not in a packaged build, so those comparisons are run where it is
  installed and recorded in `cosmos/data/validation.json`, which the app shows
  with the date it was measured and a footnote saying so. A test compares the
  record with a fresh run on every change, and `write_record` refuses to save a
  partial run, so what ships cannot quietly go stale or look more complete than it
  is. `python tools/record_validation.py` repeats the whole thing.

- **Eight lesson figures were inventing their data without saying so** (`V5`).
  The course draws 67 figures; fourteen of them make their numbers up, and eight
  of those said nothing about it. One had a legend reading "measurements" beside
  points that had been drawn from a random number generator. All eight now say
  plainly what they are, in the title, an axis label or the legend.
- **A test that finds the next one** (`V5`). Detected, not declared: every figure
  is rendered with numpy's generator under watch, and one that asked for random
  numbers — while loading none of the real data files — must carry a plain word
  such as *simulated*, *mock*, *toy* or *not real data* somewhere a reader will
  see it. "Model" and "example" do not count, because a figure of real
  measurements next to a theory curve says "model" too. The test also proves the
  watch would fire, so a guard that quietly stops working cannot pass.
- **Two figure titles ran off the edge of the picture** (`V5`). A label cut in
  half is not a label, and matplotlib neither wraps nor shrinks a long title. The
  same test now measures every title against the figure it is drawn on; it caught
  one title lengthened by the labelling above and one that had been clipped in
  `linear_vs_log` since it was written.
- **An exported plot or table now says what it is** (`V2`). A PNG in a folder and
  a CSV in a spreadsheet have lost every label the app drew around them, and a
  figure that reaches someone else's slide deck should not need the app to be
  understood. Saving a plot now writes a caption underneath it — the app and its
  version, the simulator it came from, whether the data was measured or generated,
  the sample and model behind it, and the date — and puts the same text in the
  image's metadata, for PNG and SVG alike. Exporting a table puts it above the
  numbers as comment lines, which spreadsheets skip and readers do not. The plot on
  screen is untouched: the caption is added for the save and removed again.
- **Six simulators say which of their data is on screen** (`V2`). A standing
  description cannot help with S5, S6, S16, S19 and S23, where the learner chooses
  between a real sample and one the app invented; each of those now reports the
  current choice, with the fit or the mock settings that produced the plot, and S24
  lists what was done to the WMAP map — mask, dipole, smoothing — before it was
  saved. Everywhere else the export falls back to the standing record, which says
  plainly when a simulator can show either kind. The note is in English, like the
  data set names and the citations it carries.
- **One record behind it, kept honest by tests** (`V1`). `cosmos/provenance.py`
  holds the list beside the code that loads the files, and `tests/test_provenance.py`
  fails if a file appears in `cosmos/data` without an entry, if an entry names a
  file, simulator, lesson or module that does not exist, or if the README that
  travels with the data stops agreeing with it.

### Changed

- **The last emoji left the interface** (`D3`). Phase 5 replaced the navigation's
  emoji with glyphs drawn in code, but the tabs and buttons further in kept theirs,
  and they were the ones that showed: the Reference page labelled its Models tab
  with a galaxy that Windows drew as a colour emoji, its Constants tab with a pair
  of scales that changed shape with the font, and its Formulas tab with a sigma
  wide enough to push the word beside it out of the tab. Forty-odd labels across
  the Reference and History tabs, the home, problems, review, notes and classroom
  pages, the flashcards, the challenge strip, the notes panel and nine simulators
  now carry a drawn icon instead of a character: twelve new glyphs on the same
  24x24 grid, in the same colours, on the same baseline as the text. Marks that
  live inside a sentence or a table — the ✓ ● ○ of a lesson's status, a problem's
  stars — are still characters, because an icon cannot go there.
- **Icons that follow the theme, wherever they are** (`D3`). A drawn glyph is
  painted in the theme's ink, so it has to be redrawn when the theme changes. Only
  the sidebar, the toolbar and the lesson tabs were; the rest would have kept the
  old colours. Every button, action and tab bar now leaves the glyph's name on
  itself, and the window redraws all of them at once. A glyph on a primary button
  takes that button's own ink, which also fixes the arrow on **Take the quiz**:
  it had been drawn in the page's text colour on a filled blue button since the
  icons were introduced.
- **The Turkish and Spanish interfaces kept their translations.** The labels that
  lost a symbol kept the translated words beside it, so nothing fell back to
  English; the three sentences that named a symbol — "press ☆ in the Notes panel"
  and its kind — were reworded in all three languages.

### Fixed

- **A primary button measured one width and drew another.** `INTERFACE_FONT` names
  Segoe UI on Windows and nothing anywhere else, so on Linux and macOS a widget
  still gets whatever family Qt hands back — and that family may have no semibold
  face of its own. Qt then synthesised the weight a primary button asked for, and a
  synthesised weight measures differently from the one Qt sized the button with.
  The segment buttons had this exact bug fixed in `D5`; the primary buttons kept
  it. The accent background was always the emphasis, and the weight was only making
  the width fragile.
- **A layout failure now names a culprit.** "review needs 874px, has 819px" tells
  you nothing you can act on, and when a width only misbehaves in a full test run
  there is no other way to see what moved. The check lists the widgets asking for
  the most room, which costs nothing while it is green.

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.6.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.6.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.6.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |
| Any browser | `Cosmos-0.6.0-website.zip` — the reading edition: unzip and open `index.html` |

Nothing needs to be installed: each package contains its own Python and Qt, and
every build runs `--selftest` before it is published.

## 0.5.0 — 2026-09-25

The interface work of 0.4.0, finished off: a window small enough for a 1024x768
screen and honest about it, a lesson header that carries one thing at a time, and
the last few pages that did not fit inside the smallest window.

### Changed

- **The window can be made smaller: 1024x680 instead of 1100x700** (`D5`). That is
  a classic 1024x768 screen less its taskbar, so the app now fits one. The old size
  was a guess in both directions — too wide for such a screen, and at the same time
  a promise it could not keep, since a simulator page needed 850 pixels of height
  where only 700 were allowed. The new size was measured against every page of the
  course and every simulator in three very different fonts, and the layout test
  fails if a page ever outgrows it.
- **The lesson header carries one thing at a time** (`D5`). It used to hold the
  level badge, the lesson's status, the view switch and the reading time all on one
  line, and on a narrow window the status wrapped onto two lines in the middle of
  it. The status and the reading time now share a quiet line of their own under the
  title.

### Fixed

- **Markdown tables are laid out to the width they have**, rather than to the width
  their contents would like. The report card of *Build Your Own Universe* ran 242
  pixels past the edge of its pane on a narrow window in a wide font; now its cells
  wrap. (99% of the width, not 100%: the one-pixel border is drawn outside it.)
  That report card compares four things at once, and four columns have a width
  below which they cannot be squeezed; in the smallest window its pane is narrower
  than that, so there alone it is scrolled sideways rather than clipped.
- "best quiz score" beside a lesson's status was the one line of English left
  untranslated in the interface. Both packs now carry it.

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.5.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.5.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.5.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |
| Any browser | `Cosmos-0.5.0-website.zip` — the reading edition: unzip and open `index.html` |

Nothing needs to be installed: each package contains its own Python and Qt, and
every build runs `--selftest` before it is published.

## 0.4.0 — 2026-09-25

A release about the interface rather than the course: the same 58 lessons and 29
simulators, in a window that gets out of their way. Everything that was on screen
before you asked for it is now behind a key, a page holds a readable width, the
navigation opens one section at a time, and a test keeps every page inside the
smallest window the app offers.

### Added

- **The window opens where you left it** (`D2`): its size, its position, whether it
  was maximised, and how wide you dragged the side panels. Until now it reset to
  1440x900 on every start, which sat oddly next to panels that were remembered.
- **A layout test** that opens every page — the whole course, every simulator, the
  glossary, the problems, the lesson map — at the smallest window size the app
  offers, and fails if anything has to be scrolled sideways or is cut off. Nothing
  checked this before, which is how the interface drifted into being cramped.

### Fixed

- Rows of buttons that were wider than a small window now **wrap onto the next
  line** instead of losing their last buttons: the row under a lesson (some lessons
  link to five simulators), both rows on the problem page, and the list of
  simulators on the home page.
- The **simulator and progress pages scroll up and down** when the window is too
  short for them, rather than squeezing their contents. A simulator needed 852
  pixels of height and the window allowed 700, so the controls were cut off on a
  1366x768 laptop.
- Long glossary terms are shortened with an ellipsis instead of pushing a
  horizontal scrollbar under the list.
- Plots may now be 180 pixels tall rather than 220, which is what let a simulator
  fit a short screen at all.
- The **"With the maths" button** was drawn bold when selected but measured
  unbold, so its own label did not fit inside it.
- The **"Age & lookback time"** tab in the cosmology calculator lost its `&`, which
  Qt had taken for a keyboard shortcut.
- Lesson text showed a ten-pixel sideways scrollbar on whichever lessons happened
  to sit near the edge in a given font. Qt lays a page out before it knows whether
  a vertical scrollbar is needed; when one appeared the viewport lost ten pixels
  and a full-width callout table no longer fitted. The reading panes now keep that
  width reserved at all times. Found by the new layout test, on CI, in fonts this
  machine does not have.
- The cosmic-web figure worked its Voronoi cloud out afresh on every redraw. The
  cloud never changes, so it is now computed once — which also stops scipy's
  Qhull opening a temporary file each time, something it occasionally fails to
  do on Windows and which the new layout test made fire reliably.
- The test suite now points Qt at the system fonts. Without them every glyph is the
  same empty box, so any measurement of how wide a label is would have been fiction.

### Changed

- **The simulators come in five families** (`D4`): *Measuring the universe* (6),
  *The expanding universe* (8), *Matter, dark matter and galaxies* (5), *The early
  universe* (7) and *How cosmologists work* (3). Twenty-nine names in a row was the
  one long list left in the navigation; now only the family you are working in is
  unfolded, exactly as the levels of the course behave above it. The same families
  head the simulator page and the home page. A simulator dropped into the plugins
  folder joins a family of its own at the end.
  They group by what a simulator is *for* rather than by the level a learner first
  meets it in: grouping by level would have left two families of one and one of
  eight.
- **No emoji left in the interface** (`D3`). Nineteen of the twenty-nine simulators
  already used a mathematical or geometric sign; the other ten used emoji, drawn in
  colour, at their own size, from a font that differs on every operating system.
  Each now has a sign of its own from Mathematical Operators, Arrows or Geometric
  Shapes — the MCMC explorer steps to and fro (⇌), the distance ladder has rungs
  (≣), dark matter detection is a recoil (⊗) — and two simulators no longer share
  the same one. Every sign is painted into an icon, so it sits on the text baseline
  and takes the theme's colour like the drawn glyphs do, including in the
  navigation list, where simulators had no icon at all.
- **Bookmarks, notes and search results** carry the same drawn icons instead of an
  emoji pasted into their text. A page's name is now just its name, which is also
  how it reads in an exported notes file.
- The course website exported from **File → Export the course as a website** picks
  up the new signs, since both read the same registry.
- **The window opens on the page, not on the furniture** (`D1`). The Guide, Notes
  and Tutor panels start closed and open on **F1**, **F2**, **F3** or their toolbar
  buttons; they never take more than a third of the window, and whichever you leave
  open comes back next time. Clicking a highlighted term in a lesson still brings
  the Guide with it. On a 1440-wide window a lesson now has about 1200 px instead of
  570, and a simulator's plot is no longer squeezed into a corner.
- **The navigation list keeps one section open at a time.** Opening a level folds
  the others, so the list stays about a dozen rows instead of 99. Long titles are
  shortened with an ellipsis rather than pushing a horizontal scrollbar under the
  list, and **Ctrl+B** folds the list away entirely.
- **The toolbar is down to nine controls** — navigation, back, forward, home,
  continue, search, bookmark and the three panels. Glossary, Reference, Progress,
  Review, Theme and Tour were in the toolbar, the menus and the navigation list at
  the same time; they stay in the last two.
- **One icon set, drawn in code** instead of emoji, so the glyphs share a pen, sit
  on the text baseline and look the same on Windows, macOS and Linux. They take the
  colour of the current theme.
- **Pages hold a readable width.** Lesson, reference, glossary and problem text is
  capped at about 90 characters a line and centred; the home page and the simulator
  list are held to one column instead of stretching across a wide screen. The home
  page lists each simulator on one line, with its tagline in the tooltip.
- Tabs are underlined words rather than stacked boxes, the toolbar has more air, and
  the status bar no longer holds a permanent tip — it speaks when something happens.

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.4.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.4.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.4.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |
| Any browser | `Cosmos-0.4.0-website.zip` — the reading edition: unzip and open `index.html` |

Nothing needs to be installed: each package contains its own Python and Qt, and
every build runs `--selftest` before it is published.

## 0.3.0 — 2026-09-24

A second full interface language, and with it the last open item on the roadmap:
every entry of all four phases is now ticked.

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
- The pack tests run over every bundled `.ts`: a language that ships must be
  complete, compiled, single-context and must not have lost a `{placeholder}`.

### Downloads

| Platform | File |
|---|---|
| Windows | `Cosmos-0.3.0-windows-amd64.zip` — one executable, no installer |
| macOS | `Cosmos-0.3.0-macos-arm64.zip` — an app bundle |
| Linux | `Cosmos-0.3.0-linux-x86_64.AppImage` or the equivalent `.tar.gz` |
| Any browser | `Cosmos-0.3.0-website.zip` — the reading edition: unzip and open `index.html` |

Nothing needs to be installed: each package contains its own Python and Qt, and
every build runs `--selftest` before it is published.

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
