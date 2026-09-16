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
