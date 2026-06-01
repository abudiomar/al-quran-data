# Quran Tafsir & Translation Data

Normalized per-book tafsir and translation assets for the Ayah app, sourced from [QUL (qul.tarteel.ai)](https://qul.tarteel.ai).

The book JSON files are published as **release assets** (not tracked in git). The app reads `manifest.json` to discover books and pins a release tag for immutable URLs.

## Format

Each book file is a map keyed by `surah:ayah`:

```jsonc
{
  "1:1":  { "text": "..." },                    // plain entry
  "2:8":  { "text": "...", "group": "2:8..2:9" }, // range anchor holds the text
  "2:9":  { "ref": "2:8" }                       // range member -> points at anchor
}
```

Translations use the same shape (no ranges). Footnotes are inlined as parentheticals.
