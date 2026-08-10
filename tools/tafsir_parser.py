import re

import html5lib


_NOTE = re.compile(r"\[\[(.*?)\]\]", re.DOTALL)
_KNOWN_TAGS = {"div", "p", "h3", "span"}
_KNOWN_CLASSES = {"ar", "sep", "hlt", "qpc-hafs", "ayah-tag"}


def parse_tafsir_html(source):
    footnotes = []
    blocks = []
    diagnostics = []

    def html_to_plain(fragment):
        parsed = html5lib.parseFragment(
            fragment, treebuilder="etree", namespaceHTMLElements=False
        )
        parts = []

        def walk(element):
            if element.text:
                parts.append(element.text)
            for child in element:
                if child.tag in {"p", "h3", "br"} and parts and not parts[-1].endswith("\n"):
                    parts.append("\n")
                walk(child)
                if child.tag in {"p", "h3", "br"} and parts and not parts[-1].endswith("\n"):
                    parts.append("\n")
                if child.tail:
                    parts.append(child.tail)

        walk(parsed)
        return "\n".join(line.strip() for line in "".join(parts).splitlines() if line.strip())

    def replace_note(match):
        note_id = len(footnotes) + 1
        footnotes.append({"id": note_id, "text": html_to_plain(match.group(1))})
        return f'<span data-tafsir-footnote="{note_id}"></span>'

    structured_source = _NOTE.sub(replace_note, source)
    root = html5lib.parseFragment(
        structured_source, treebuilder="etree", namespaceHTMLElements=False
    )
    plain_root = html5lib.parseFragment(
        source, treebuilder="etree", namespaceHTMLElements=False
    )

    def report(value):
        if value not in diagnostics:
            diagnostics.append(value)

    def inspect(element):
        if element.tag not in _KNOWN_TAGS:
            report(f"unknown_tag:{element.tag}")
        for class_name in element.attrib.get("class", "").split():
            if class_name not in _KNOWN_CLASSES:
                report(f"unknown_class:{class_name}")

    def add_text(spans, text, kind="text"):
        if not text:
            return
        spans.append({"type": kind, "text": text})

    def walk_inline(element, spans, kind="text"):
        add_text(spans, element.text, kind)
        for child in element:
            inspect(child)
            classes = set(child.attrib.get("class", "").split())
            note_id = child.attrib.get("data-tafsir-footnote")
            if note_id:
                spans.append({"type": "footnote_reference", "id": int(note_id)})
            elif "qpc-hafs" in classes:
                walk_inline(child, spans, "quran")
            elif "ayah-tag" in classes:
                walk_inline(child, spans, "ayah_reference")
            else:
                walk_inline(child, spans, kind)
            add_text(spans, child.tail, kind)

    def add_block(element):
        classes = set(element.attrib.get("class", "").split())
        if "sep" in classes:
            blocks.append({"type": "separator"})
            return
        spans = []
        walk_inline(element, spans)
        blocks.append({
            "type": "heading" if element.tag == "h3" else "paragraph",
            "spans": spans,
        })

    def flush_pending(spans):
        if spans and any(
            span["type"] == "footnote_reference" or span.get("text", "").strip()
            for span in spans
        ):
            blocks.append({"type": "paragraph", "spans": spans.copy()})
        spans.clear()

    def walk_container(element):
        pending = []
        add_text(pending, element.text)
        for child in element:
            inspect(child)
            if child.tag in {"p", "h3"}:
                flush_pending(pending)
                add_block(child)
            elif any(descendant.tag in {"p", "h3"} for descendant in child.iter()):
                flush_pending(pending)
                walk_container(child)
            else:
                classes = set(child.attrib.get("class", "").split())
                note_id = child.attrib.get("data-tafsir-footnote")
                if note_id:
                    pending.append({"type": "footnote_reference", "id": int(note_id)})
                elif "qpc-hafs" in classes:
                    walk_inline(child, pending, "quran")
                elif "ayah-tag" in classes:
                    walk_inline(child, pending, "ayah_reference")
                else:
                    walk_inline(child, pending)
            add_text(pending, child.tail)
        flush_pending(pending)

    walk_container(root)
    if source.count("[[") != source.count("]]" ):
        report("unclosed_footnote")

    return {
        "blocks": blocks,
        "footnotes": footnotes,
        "plain_text": "".join(plain_root.itertext()),
        "diagnostics": diagnostics,
    }


def structure_book(source):
    structured = {}
    for ayah_key, entry in source.items():
        if isinstance(entry, str):
            if entry not in source:
                raise ValueError(f"{ayah_key}: broken reference to {entry}")
            structured[ayah_key] = entry
            continue
        if isinstance(entry, dict) and entry.get("ref"):
            reference = str(entry["ref"])
            if reference not in source:
                raise ValueError(f"{ayah_key}: broken reference to {reference}")
            structured[ayah_key] = reference
            continue
        if not isinstance(entry, dict) or not str(entry.get("text", "")).strip():
            raise ValueError(f"{ayah_key}: missing tafsir text")

        parsed = parse_tafsir_html(entry["text"])
        result = {
            "source_html": entry["text"],
            "plain_text": parsed["plain_text"],
            "blocks": parsed["blocks"],
            "footnotes": parsed["footnotes"],
        }
        if entry.get("ayah_keys"):
            result["ayah_keys"] = entry["ayah_keys"]
        if parsed["diagnostics"]:
            result["diagnostics"] = parsed["diagnostics"]
        structured[ayah_key] = result
    return structured
