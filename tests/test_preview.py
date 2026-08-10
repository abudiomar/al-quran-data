from pathlib import Path
import unittest


PREVIEW = (Path(__file__).parents[1] / "preview.html").read_text(encoding="utf-8")


class PreviewTest(unittest.TestCase):
    def test_loads_requested_ayah_from_cors_enabled_qul_api(self):
        self.assertIn("https://qul.tarteel.ai/api/v1/tafsirs/14/by_range", PREVIEW)
        self.assertNotIn("releases/download/v1.1/ibn_kathir.structured.json", PREVIEW)


if __name__ == "__main__":
    unittest.main()
