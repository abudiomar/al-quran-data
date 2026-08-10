import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.build_tafsir_sqlite import build_database
from tools.tafsir_parser import parse_tafsir_html, structure_book


class TafsirParserTest(unittest.TestCase):
    def test_builds_anchor_based_mobile_database(self):
        book = {
            "2:8": {
                "source_html": "<p>archival only</p>",
                "plain_text": "تفسير",
                "blocks": [{"type": "paragraph", "spans": [
                    {"type": "text", "text": "تفسير"}
                ]}],
                "footnotes": [],
                "ayah_keys": ["2:8", "2:9"],
            },
            "2:9": "2:8",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tafsir.sqlite"
            build_database(book, path, edition_id="test")
            database = sqlite3.connect(path)
            documents = database.execute(
                "SELECT anchor_key, blocks_json FROM tafsir_documents"
            ).fetchall()
            mappings = database.execute(
                "SELECT ayah_key, anchor_key FROM tafsir_ayah_map ORDER BY ayah_key"
            ).fetchall()
            database.close()

        self.assertEqual(len(documents), 1)
        self.assertNotIn("source_html", documents[0][1])
        self.assertEqual(mappings, [("2:8", "2:8"), ("2:9", "2:8")])

    def test_manifest_publishes_structured_long_tafsir_assets(self):
        manifest = json.loads(
            (Path(__file__).parents[1] / "manifest.json").read_text(encoding="utf-8")
        )
        books = {book["id"]: book for book in manifest["books"]}

        for book_id in (
            "muyassar",
            "saadi",
            "ibn_kathir",
            "tabari",
            "baghawi",
            "mukhtasar_ar",
            "mukhtasar_en",
        ):
            with self.subTest(book_id=book_id):
                book = books[book_id]
                self.assertEqual(
                    book["structured_asset"], f"{book_id}.structured.json"
                )
                self.assertEqual(book["structured_format"], "tafsir_blocks_v1")
                self.assertRegex(book["structured_sha256"], r"^[0-9a-f]{64}$")
                self.assertEqual(
                    book["structured_sqlite_asset"],
                    f"{book_id}.structured.sqlite.gz",
                )
                self.assertRegex(
                    book["structured_sqlite_sha256"], r"^[0-9a-f]{64}$"
                )

        self.assertEqual(books["saadi"]["ayah_count"], 6177)
        self.assertEqual(books["saadi"]["coverage_status"], "source_incomplete")

    def test_parses_ibn_kathir_paragraph_semantics(self):
        source = (
            '<div class="ar" lang="ar"><p>قال تعالى: '
            '<span class="hlt"><span class="qpc-hafs">﴿الْحَمْدُ لِلَّهِ﴾</span></span> '
            '<span class="ayah-tag">[الفاتحة: ٢]</span> '
            '[[في أ: الحمد لله رب العالمين.]] ثم قال.</p></div>'
        )

        result = parse_tafsir_html(source)

        self.assertEqual(result["blocks"], [
            {
                "type": "paragraph",
                "spans": [
                    {"type": "text", "text": "قال تعالى: "},
                    {"type": "quran", "text": "﴿الْحَمْدُ لِلَّهِ﴾"},
                    {"type": "text", "text": " "},
                    {"type": "ayah_reference", "text": "[الفاتحة: ٢]"},
                    {"type": "text", "text": " "},
                    {"type": "footnote_reference", "id": 1},
                    {"type": "text", "text": " ثم قال."},
                ],
            }
        ])
        self.assertEqual(result["footnotes"], [
            {"id": 1, "text": "في أ: الحمد لله رب العالمين."}
        ])

    def test_preserves_unwrapped_text_after_separator(self):
        source = (
            '<div><p>المقطع الأول.</p><p class="sep">* * *</p>'
            'المقطع الثاني <span class="qpc-hafs">﴿آية﴾</span>.</div>'
        )

        result = parse_tafsir_html(source)

        self.assertEqual([block["type"] for block in result["blocks"]], [
            "paragraph", "separator", "paragraph"
        ])
        self.assertEqual(result["blocks"][2]["spans"], [
            {"type": "text", "text": "المقطع الثاني "},
            {"type": "quran", "text": "﴿آية﴾"},
            {"type": "text", "text": "."},
        ])

    def test_preserves_malformed_note_and_reports_it(self):
        result = parse_tafsir_html('<p>متن [[حاشية غير مكتملة</p>')

        self.assertEqual(result["blocks"][0]["spans"], [
            {"type": "text", "text": "متن [[حاشية غير مكتملة"}
        ])
        self.assertEqual(result["diagnostics"], ["unclosed_footnote"])

    def test_reports_unknown_markup_without_dropping_text(self):
        result = parse_tafsir_html(
            '<section class="future"><p>قبل <mark>مهم</mark> بعد</p></section>'
        )

        self.assertEqual(result["plain_text"], "قبل مهم بعد")
        self.assertEqual(result["diagnostics"], [
            "unknown_tag:section", "unknown_class:future", "unknown_tag:mark"
        ])

    def test_extracts_footnote_that_contains_source_paragraphs(self):
        result = parse_tafsir_html(
            '<p>المتن [[السطر الأول.</p><p>السطر الثاني.]] بقية المتن.</p>'
        )

        self.assertEqual(result["footnotes"], [
            {"id": 1, "text": "السطر الأول.\nالسطر الثاني."}
        ])
        self.assertEqual(
            sum(
                span.get("type") == "footnote_reference"
                for block in result["blocks"]
                for span in block.get("spans", [])
            ),
            1,
        )

    def test_structures_anchor_and_preserves_range_reference(self):
        source = {
            "2:8": {
                "text": "<p>تفسير <span class=\"qpc-hafs\">﴿آية﴾</span></p>",
                "ayah_keys": ["2:8", "2:9"],
            },
            "2:9": "2:8",
        }

        result = structure_book(source)

        self.assertEqual(result["2:9"], "2:8")
        self.assertEqual(result["2:8"]["ayah_keys"], ["2:8", "2:9"])
        self.assertEqual(result["2:8"]["source_html"], source["2:8"]["text"])
        self.assertEqual(result["2:8"]["blocks"][0]["spans"][1], {
            "type": "quran", "text": "﴿آية﴾"
        })

    def test_structures_object_reference_used_by_short_tafsirs(self):
        result = structure_book({
            "2:3": {"text": "تفسير الآيتين", "group": "2:3..2:4"},
            "2:4": {"ref": "2:3"},
        })

        self.assertEqual(result["2:4"], "2:3")

    def test_preserves_standalone_footnote_between_blocks(self):
        result = parse_tafsir_html(
            '<p>قبل</p><p class="sep">* * *</p>[[زيادة من ت، أ.]]<p>بعد</p>'
        )

        references = [
            span
            for block in result["blocks"]
            for span in block.get("spans", [])
            if span["type"] == "footnote_reference"
        ]
        self.assertEqual(references, [{"type": "footnote_reference", "id": 1}])


if __name__ == "__main__":
    unittest.main()
