"""Parse and chunk the full NEC 2017 text for storage in ``nec_chunks``.

The source text is a line-oriented PDF extraction. Everything that is not
whitespace is preserved, so a coverage check can prove the whole book made it
into the database.

Chunks carry enough metadata (article / section / titles) to make search
results useful instead of anonymous 4 kB blobs.
"""

from __future__ import annotations

import gzip
import os
import re
from dataclasses import dataclass, field

DEFAULT_SOURCE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "nec_2017.txt")

CHUNKER_VERSION = 2
TARGET_CHARS = 2200
MAX_CHARS = 3400

# "ARTICLE 220" on its own line starts an article body (table-of-contents
# entries and running page headers keep a title, so they don't match).
ARTICLE_HEAD = re.compile(r"^ARTICLE\s+(\d{1,4})\s*$")
# Running page header: "ARTICLE 220 — BRANCH-CIRCUIT, FEEDER, ..."
ARTICLE_HEADER = re.compile(r"^ARTICLE\s+\d{1,4}\s*[—–-]\s*\S")
# "220.42 General Lighting. The demand factors ..." (title must be short)
SECTION_HEAD = re.compile(r"^(\d{3}\.\d{1,4})\.?\s+([A-Z][^.]{0,90})\.(?:\s|$)")
SECTION_BARE = re.compile(r"^(\d{3}\.\d{1,4})\s*$")
ANNEX_HEAD = re.compile(r"^INFORMATIVE ANNEX\s+([A-Z])\s*$")
INDEX_HEAD = re.compile(r"^Index\s*$")
PART_HEAD = re.compile(r"^Part\s+[IVX]+\.?\s")


@dataclass
class _Unit:
    article: str
    title: str | None
    section: str | None
    section_title: str | None
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip("\n")


def read_source(path: str | None = None) -> str:
    """Read the NEC text, supporting a plain .txt or a .txt.gz next to it."""
    path = path or DEFAULT_SOURCE
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as fh:
                return fh.read()
        gz = path + ".gz"
        if os.path.exists(gz):
            with gzip.open(gz, "rt", encoding="utf-8", errors="ignore") as fh:
                return fh.read()
    except OSError:
        return ""
    return ""


def _is_article_heading(line: str) -> int | None:
    m = ARTICLE_HEAD.match(line)
    return int(m.group(1)) if m else None


def _section_for(line: str, article: int | None) -> tuple[str, str | None] | None:
    if article is None:
        return None
    m = SECTION_HEAD.match(line)
    if m:
        section, title = m.group(1), m.group(2).strip()
    else:
        m = SECTION_BARE.match(line)
        if not m:
            return None
        section, title = m.group(1), None
    try:
        prefix = int(section.split(".")[0])
    except ValueError:
        return None
    if prefix != article:
        return None
    return section, title


def parse_units(text: str) -> list[_Unit]:
    """Split the source into article/section-aware units, preserving all text."""
    lines = text.splitlines()
    units: list[_Unit] = []

    article: int | None = None
    article_title: str | None = None
    section: str | None = None
    section_title: str | None = None
    current = _Unit("front", "Front Matter", None, None)
    collecting_title = False
    title_parts: list[str] = []

    def flush() -> None:
        nonlocal current
        if current.lines:
            units.append(current)
        label = str(article) if article is not None else "front"
        current = _Unit(label, article_title, section, section_title)

    def finish_title() -> None:
        nonlocal collecting_title
        collecting_title = False

    for raw in lines:
        line = raw.rstrip()

        art = _is_article_heading(line)
        if art is not None:
            flush()
            article = art
            article_title = None
            section = None
            section_title = None
            title_parts = []
            collecting_title = True
            current = _Unit(str(article), None, None, None)
            current.lines.append(line)
            continue

        annex = ANNEX_HEAD.match(line)
        if annex:
            flush()
            article = None
            article_title = f"Informative Annex {annex.group(1)}"
            section = None
            section_title = None
            collecting_title = False
            current = _Unit(f"annex-{annex.group(1)}", article_title, None, None)
            current.lines.append(line)
            continue

        if INDEX_HEAD.match(line) and current.article != "index":
            flush()
            article = None
            article_title = "Index"
            section = None
            section_title = None
            collecting_title = False
            current = _Unit("index", "Index", None, None)
            current.lines.append(line)
            continue

        # Chapter 9 (tables) follows Article 840 and has no ARTICLE heading.
        if line.strip() == "Chapter 9 Tables" and article == 840:
            flush()
            article = None
            article_title = "Chapter 9 Tables"
            section = None
            section_title = None
            collecting_title = False
            current = _Unit("chapter-9", article_title, None, None)
            current.lines.append(line)
            continue

        # Titles wrap across up to three lines in the PDF extraction. Collect
        # them until a blank line, a Part heading, or a section heading.
        if collecting_title:
            stripped = line.strip()
            if (
                not stripped
                or len(title_parts) >= 3
                or ARTICLE_HEADER.match(stripped)
                or PART_HEAD.match(stripped)
                or _section_for(stripped, article) is not None
            ):
                finish_title()
            elif len(stripped) > 80 or "." in stripped or not stripped[0].isupper():
                # Body text, not a wrapped title line.
                finish_title()
            else:
                title_parts.append(stripped)
                article_title = " ".join(title_parts)[:280]
                current.title = article_title
                current.lines.append(line)
                continue

        found = _section_for(line, article)
        if found:
            new_section, new_title = found
            if new_section != section:
                flush()
                section, section_title = new_section, new_title
                current.section = section
                current.section_title = section_title

        current.lines.append(line)

    flush()
    return [u for u in units if u.text]


def _split_long_line(line: str, limit: int) -> list[str]:
    """Break a single over-long line at word boundaries."""
    if len(line) <= limit:
        return [line]
    parts: list[str] = []
    start = 0
    while start < len(line):
        end = min(start + limit, len(line))
        if end < len(line):
            space = line.rfind(" ", start, end)
            if space > start + limit // 2:
                end = space + 1
        parts.append(line[start:end])
        start = end
    return parts


def _split_oversized(unit: _Unit, limit: int) -> list[_Unit]:
    """Split a unit longer than ``limit`` at line boundaries."""
    pieces: list[_Unit] = []
    buf: list[str] = []
    size = 0
    for line in unit.lines:
        for part in _split_long_line(line, limit):
            if buf and size + len(part) + 1 > limit:
                pieces.append(_Unit(unit.article, unit.title, unit.section, unit.section_title, buf))
                buf, size = [], 0
            buf.append(part)
            size += len(part) + 1
    if buf:
        pieces.append(_Unit(unit.article, unit.title, unit.section, unit.section_title, buf))
    return pieces


def build_chunks(text: str, target: int = TARGET_CHARS, maximum: int = MAX_CHARS) -> list[dict]:
    """Build DB-ready chunk dicts with metadata. No text is dropped."""
    units = parse_units(text)
    chunks: list[dict] = []
    buf: list[_Unit] = []
    size = 0

    def emit() -> None:
        nonlocal buf, size
        if not buf:
            return
        merged = _Unit(buf[0].article, buf[0].title, buf[0].section, buf[0].section_title)
        for u in buf:
            merged.lines.extend(u.lines)
        chunks.append(_chunk_dict(merged))
        buf, size = [], 0

    for unit in units:
        if len(unit.text) > maximum:
            emit()
            chunks.extend(_chunk_dict(piece) for piece in _split_oversized(unit, maximum))
            continue
        if buf and (
            buf[0].article != unit.article
            or buf[0].section != unit.section
            or size + len(unit.text) + 1 > maximum
        ):
            emit()
        buf.append(unit)
        size += len(unit.text) + 1
        if size >= target:
            emit()
    emit()
    return chunks


def _chunk_dict(unit: _Unit) -> dict:
    return {
        "article": unit.article,
        "title": (unit.title or "")[:280] or None,
        "section": unit.section,
        "section_title": (unit.section_title or "")[:280] or None,
        "content": unit.text,
    }


def _norm(value: str) -> str:
    return re.sub(r"\s+", "", value)


def coverage(source: str, chunks: list[dict]) -> float:
    """Fraction of the source (whitespace-insensitive) present in the chunks."""
    total = len(_norm(source))
    if not total:
        return 0.0
    return len(_norm("\n".join(c["content"] for c in chunks))) / total


def article_list(chunks: list[dict]) -> list[str]:
    """Unique article identifiers, numeric articles first."""
    seen = {c["article"] for c in chunks if c.get("article")}
    return sorted(seen, key=article_sort_key)


def article_sort_key(article: str) -> tuple[int, int | str]:
    if article.isdigit():
        return (0, int(article))
    if article.startswith("annex-"):
        return (1, article)
    if article == "index":
        return (2, article)
    return (3, article)
