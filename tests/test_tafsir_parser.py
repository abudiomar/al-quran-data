import unittest

from tools.tafsir_parser import parse_tafsir_html, structure_book


class TafsirParserTest(unittest.TestCase):
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
