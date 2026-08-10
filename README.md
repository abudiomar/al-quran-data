# Quran Tafsir & Translation Data

Normalized per-book tafsir and translation assets for the Ayah app, sourced from [QUL (qul.tarteel.ai)](https://qul.tarteel.ai).

The book JSON files are published as **release assets** (not tracked in git). The app reads `manifest.json` to discover books and pins a release tag for immutable URLs.

Long Arabic tafsirs preserve QUL's source HTML. This keeps paragraph boundaries,
Quran quotation spans, ayah-reference tags, and editorial footnotes available to
clients. Clients must render an allowlisted subset of this HTML; use plain-text
conversion only for search, copy, and accessibility fallbacks.

## Format

Each book file is a map keyed by `surah:ayah`:

```jsonc
{
  "1:1":  { "text": "<div><p>...</p></div>" },
  "2:8":  { "text": "<p>...</p>", "ayah_keys": ["2:8", "2:9"] },
  "2:9":  "2:8"
}
```

Translations use the same shape without ranges. QUL editorial footnotes remain
inline in the source HTML so clients can parse and present them without losing
the original text.

Regenerate the structured long-tafsir assets with:

```powershell
pwsh ./tools/fetch_qul_tafsirs.ps1 -OutputDirectory ./dist
python -m tools.structure_tafsir ./dist/ibn_kathir.json ./dist/ibn_kathir.structured.json
python -m tools.structure_tafsir ./dist/baghawi.json ./dist/baghawi.structured.json
```

Structured anchors retain `source_html` and add `plain_text`, semantic `blocks`,
and extracted `footnotes`. Range members remain string references to their
anchor, matching the raw asset.
