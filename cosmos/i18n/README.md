# Interface translations

The course itself — lessons, quizzes, the glossary, the formula sheet — is
written in English and stays that way. The **interface** (menus, buttons, page
headings) can be translated, and this folder is where translations live.

To add one, from the project root:

```bash
python tools/update_translations.py --language de   # writes cosmos_de.ts here
pyside6-linguist cosmos/i18n/cosmos_de.ts               # translate it
python tools/update_translations.py --release       # compiles cosmos_de.qm
```

The language then appears in **View → Language** and is used the next time
Cosmos starts. Strings are marked in the source with `cosmos.i18n.tr(...)` and
are looked up in the `cosmos` context.

Only `.qm` files are loaded at run time; `.ts` files are the editable source.

`cosmos_tr.ts` / `cosmos_tr.qm` are the Turkish pack that ships with the app. It
covers the window chrome, the pages, the panels, the badges, the Guide panel, the
guided tour and every simulator's controls, tooltips and guidance. Lesson text and
the values a simulator reports back are English. Strings that are defined far from
where they are shown (the badge table or the simulator catalogue, for instance) are
marked with `tr_noop()` and translated with `tr()` at display time — the update
script tells lupdate about that alias.

Refreshing a `.ts` is safe: lupdate cannot see the `cosmos` context and marks every
existing entry obsolete, so `update_translations.py` remembers the translations
beforehand and writes them back, dropping only the entries whose source string has
really disappeared.
