# Translating Cosmos

Thank you for considering it. A translation is what turns this from an app
somebody can use into one they can learn from, and it is the one contribution
that needs no Python at all.

Cosmos ships with **Turkish** (Türkçe) and **Spanish** (Español). Any other
language is welcome.

## What is translated, and what is not

| Translated | Left in English |
|---|---|
| Menus, buttons, tabs, tooltips, dialogs | Lesson text |
| The Guide panel and the guided tour | Quiz questions and their explanations |
| Simulator names, taglines, controls, results | The glossary and the formula sheet |
| Challenges, hints and their success messages | Worked problems |
| Badges, the progress report, teacher notes headings | Names of datasets, surveys, galaxies and epochs |

The course itself stays in English on purpose. Cosmology is read in English, the
lessons cite English papers, and a learner who finishes the course should
recognise the words when they meet them again. What the interface does is get
out of the way while that happens.

Proper names stay as they are: *Planck*, *WMAP*, *SPARC*, *Pantheon+*, *Big
Bang*, *Big Crunch*, *Big Rip*, *DESI*, *Euclid*, *GW170817*. So do symbols and
units: `Ωm`, `H0`, `Mpc/h`, `µK`, `M☉`.

## Starting a language

From the project root, with the development requirements installed:

```bash
python tools/update_translations.py --language de
```

That writes `cosmos/i18n/cosmos_de.ts` — an XML file with one `<message>` per
string, each holding the English `<source>` and an empty `<translation>`. Use the
[two-letter code](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)
for your language.

Translate it in Qt Linguist, which is made for exactly this and shows each
string's context:

```bash
pyside6-linguist cosmos/i18n/cosmos_de.ts
```

Editing the XML in a text editor works too. Remove `type="unfinished"` from the
`<translation>` tag when you have filled it in.

Then compile it and start the app:

```bash
python tools/update_translations.py --release
python main.py
```

Your language now appears under **View → Language**. It applies the next time
Cosmos starts.

## Six rules that matter

1. **Keep every `{placeholder}` exactly as it is.** `{count}`, `{path}`,
   `{h0}` are filled in with numbers at run time. Reorder them freely — that is
   what they are for — but never rename or drop one. A missing placeholder
   crashes the page that shows it, and a test refuses the translation.
2. **Keep the HTML.** Many strings contain `<b>`, `<br>`, `<i>` or
   `<span style='…'>`. Move the tags to where the emphasis belongs in your
   language, but keep them paired and spelled the same.
3. **`&` marks a keyboard shortcut, `&&` is a literal ampersand.** In `&File`
   the letter after `&` is the Alt key that opens the menu; put it on a letter
   that makes sense in your language, and do not give two menus the same one.
   `Constants && units` shows as *Constants & units*.
4. **Do not translate the shortcuts themselves.** `(Ctrl+F)`, `(F1)`, `Alt+Left`
   are keys on the keyboard, not words. Translate the key *names* only if your
   language conventionally does (`Mayús` for Shift in Spanish, say).
5. **Numbers follow your language.** If your language writes decimals with a
   comma, write `0,3` and `2,725 K`. Keep the digits themselves as they are —
   they come from measurements.
6. **Markdown strings keep their structure.** A few long strings are whole Guide
   pages in Markdown. Keep the `##` headings, the `-` bullets, the blank lines
   and anything between `$…$` (those are formulas) exactly where they are.

## Physics words

Strings such as `flat`, `accelerates forever` or `billion years` come from the
physics layer, which knows nothing about the interface. They are listed in
[`cosmos/gui/labels.py`](cosmos/gui/labels.py) and reach your `.ts` like any
other string. They are short and they appear inside longer sentences, so check
how they read there — for example `Fate: this universe {fate}.`

Decide your terminology once and keep it. The two existing packs settled on:

| English | Turkish | Spanish |
|---|---|---|
| redshift | kırmızıya kayma | corrimiento al rojo |
| dark matter / dark energy | karanlık madde / karanlık enerji | materia oscura / energía oscura |
| scale factor | ölçek faktörü | factor de escala |
| comoving distance | eşhareketli uzaklık | distancia comóvil |
| halo | halo | halo |
| survey | tarama | sondeo |
| lesson / quiz / challenge | ders / quiz / meydan okuma | lección / cuestionario / reto |
| badge / streak | rozet / seri | insignia / racha |

## Checking your work

```bash
pytest tests/test_i18n.py -q
```

The tests check that every string is translated, that no `{placeholder}` was
lost, and that the pack loads and reaches the simulators. Then open the app and
walk through it: the home page, a lesson, a simulator with its challenge bar, the
Guide panel, and **Help → Keyboard shortcuts**. Text that is much longer than the
English can push a button out of its dialog; that is worth catching before anyone
else sees it.

If you add strings to the app while translating, or the app changes under you,
run `python tools/update_translations.py` again. It keeps everything already
translated and only adds what is new — refreshing is safe.

## Sending it in

Open a pull request with `cosmos/i18n/cosmos_<code>.ts` and its compiled
`cosmos_<code>.qm`. Say which language it is and whether it is complete; a partial
pack is fine and useful, because untranslated strings simply fall back to English.

If the language is not in `LANGUAGE_NAMES` in
[`cosmos/i18n.py`](cosmos/i18n.py), add it there with its own name — *Deutsch*,
not *German* — so the menu shows it the way its speakers write it.
