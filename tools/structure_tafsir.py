import argparse
import json
from pathlib import Path

from tools.tafsir_parser import structure_book


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as source_file:
        source = json.load(source_file)
    structured = structure_book(source)

    diagnostics = [
        (key, item["diagnostics"])
        for key, item in structured.items()
        if isinstance(item, dict) and item.get("diagnostics")
    ]
    if diagnostics:
        raise ValueError(f"Unresolved parser diagnostics: {diagnostics[:20]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(structured, output_file, ensure_ascii=False, separators=(",", ":"))

    anchors = sum(isinstance(item, dict) for item in structured.values())
    print(f"Wrote {args.output}: {len(structured)} ayahs, {anchors} anchors")


if __name__ == "__main__":
    main()
