# OceanAtmosWiki Markdown Export

This repository contains a MediaWiki XML dump (`oceanwiki-20250908.xml`). The
binary attachment files are **not** tracked in git – the tree would exceed the
PR size limits – but `convert_dump.py` can link to them (and optionally copy
them) when they are present on disk.

## Usage

```bash
python3 convert_dump.py oceanwiki-20250908.xml --output site
```

The command recreates the `site/` directory with:

- `index.md` – a table of contents linking to each exported page.
- `pages/` – Markdown versions of the wiki pages in the selected namespaces.
- `attachments/` – copies of the referenced files preserved with their original names (only when `--copy-attachments` is supplied).
- `attachments-manifest.txt` – a TSV summary describing each referenced attachment and whether it was copied.

By default, only the main namespace (ID `0`) is exported. You can include
additional namespaces with `--namespaces`, for example:

```bash
python3 convert_dump.py oceanwiki-20250908.xml --attachments /path/to/oceanwiki --output site --copy-attachments
```

Place the extracted MediaWiki `images/` tree (often called `oceanwiki/` in dump
archives) anywhere on disk and point `--attachments` at it. When the directory
is missing, or when `--copy-attachments` is omitted, the Markdown pages still
link to the files but the manifest will mark them as "not copied" so you can
retrieve them later.

Running the converter removes any existing `site/` directory before rebuilding it.
