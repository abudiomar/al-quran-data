import argparse
import json
from pathlib import Path
import sqlite3


def build_database(book, output_path, *, edition_id):
    output_path = Path(output_path)
    output_path.unlink(missing_ok=True)
    database = sqlite3.connect(output_path)
    try:
        database.executescript("""
            CREATE TABLE tafsir_documents (
                edition_id TEXT NOT NULL,
                anchor_key TEXT NOT NULL,
                plain_text TEXT NOT NULL,
                blocks_json TEXT NOT NULL,
                footnotes_json TEXT NOT NULL,
                ayah_keys_json TEXT NOT NULL,
                PRIMARY KEY (edition_id, anchor_key)
            );
            CREATE TABLE tafsir_ayah_map (
                edition_id TEXT NOT NULL,
                ayah_key TEXT NOT NULL,
                anchor_key TEXT NOT NULL,
                PRIMARY KEY (edition_id, ayah_key)
            );
            CREATE INDEX idx_tafsir_ayah_lookup
                ON tafsir_ayah_map (edition_id, ayah_key);
        """)
        documents = []
        mappings = []
        for ayah_key, entry in book.items():
            anchor_key = entry if isinstance(entry, str) else ayah_key
            mappings.append((edition_id, ayah_key, anchor_key))
            if isinstance(entry, str):
                if entry not in book or isinstance(book[entry], str):
                    raise ValueError(f"{ayah_key}: broken reference to {entry}")
                continue
            documents.append((
                edition_id,
                anchor_key,
                entry.get("plain_text", ""),
                json.dumps(entry.get("blocks", []), ensure_ascii=False, separators=(",", ":")),
                json.dumps(entry.get("footnotes", []), ensure_ascii=False, separators=(",", ":")),
                json.dumps(entry.get("ayah_keys", [ayah_key]), ensure_ascii=False, separators=(",", ":")),
            ))
        database.executemany(
            "INSERT INTO tafsir_documents VALUES (?, ?, ?, ?, ?, ?)", documents
        )
        database.executemany(
            "INSERT INTO tafsir_ayah_map VALUES (?, ?, ?)", mappings
        )
        database.commit()
    finally:
        database.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--edition-id", required=True)
    args = parser.parse_args()
    with args.source.open(encoding="utf-8") as source_file:
        book = json.load(source_file)
    build_database(book, args.output, edition_id=args.edition_id)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
