import html
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.calculations.nec220 import _MULTIFAMILY_FACTORS
from app.database import SessionLocal, get_db
from app.models import NECChunk, NECTable
from app.services.nec_ingest import (
    CHUNKER_VERSION,
    DEFAULT_SOURCE,
    article_sort_key,
    build_chunks,
    coverage,
    read_source,
)

NEC_PATH = os.path.abspath(DEFAULT_SOURCE)

_text_cache = None
_coverage_cache: dict[int, dict] = {}

# Articles an estimator reaches for most often get a small search boost.
_ARTICLE_BOOST = {"220": 6, "210": 4, "250": 3, "110": 2, "230": 2, "240": 2, "430": 1}


def _read_file() -> str:
    return read_source(NEC_PATH)


def _needs_seed(db: Session) -> bool:
    total = db.query(NECChunk).count()
    if total == 0:
        return True
    # Older ingests have no article metadata; re-ingest so search keeps context.
    missing = db.query(NECChunk).filter(NECChunk.article.is_(None)).count()
    return missing > 0


def seed_nec_chunks(db: Session | None = None, force: bool = False) -> int:
    """Ingest the full NEC 2017 text into nec_chunks. Returns number inserted."""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        if not force and not _needs_seed(db):
            return 0
        text = _read_file()
        if not text:
            return 0
        chunks = build_chunks(text)
        if not chunks:
            return 0
        db.query(NECChunk).delete()
        batch: list[NECChunk] = []
        for index, chunk in enumerate(chunks):
            batch.append(
                NECChunk(
                    chunk_index=index,
                    article=chunk["article"],
                    section=chunk["section"],
                    title=chunk["title"],
                    section_title=chunk["section_title"],
                    content=chunk["content"],
                )
            )
            if len(batch) >= 400:
                db.add_all(batch)
                db.commit()
                batch = []
        if batch:
            db.add_all(batch)
        db.commit()
        _coverage_cache.clear()
        return len(chunks)
    finally:
        if own:
            db.close()


_TABLE_FALLBACKS = {
    "220.42": {
        "description": "Lighting Load Demand Factors (Dwelling units)",
        "rows": [
            {"portion": "First 3000 VA", "factor": "100%"},
            {"portion": "3001 to 120,000 VA", "factor": "35%"},
            {"portion": "Remainder over 120,000 VA", "factor": "25%"},
        ],
    },
    "220.54": {
        "description": "Demand Factors for Household Electric Clothes Dryers",
        "rows": [
            {"dryers": "1-4", "factor": "100%"},
            {"dryers": "5", "factor": "85%"},
            {"dryers": "6", "factor": "75%"},
            {"dryers": "7", "factor": "65%"},
            {"dryers": "8", "factor": "60%"},
            {"dryers": "9", "factor": "55%"},
            {"dryers": "10", "factor": "50%"},
            {"dryers": "11", "factor": "47%"},
            {"dryers": "12-23", "factor": "47% - 1%/dryer over 11"},
            {"dryers": "24-42", "factor": "35% - 0.5%/dryer over 23"},
            {"dryers": "43+", "factor": "25%"},
        ],
    },
    "220.55": {
        "description": "Demand Factors and Loads for Household Electric Ranges (Column C, not over 12 kW)",
        "rows": [
            {"ranges": n, "max_demand_kw": v}
            for n, v in {
                1: 8, 2: 11, 3: 14, 4: 17, 5: 20, 6: 21, 7: 22, 8: 23, 9: 24, 10: 25,
                11: 26, 12: 27, 13: 28, 14: 29, 15: 30, 16: 31, 17: 32, 18: 33, 19: 34,
                20: 35, 21: 36, 22: 37, 23: 38, 24: 39, 25: 40,
            }.items()
        ],
    },
    "220.84": {
        "description": "Optional Calculations — Demand Factors for Three or More Multifamily Dwelling Units",
        "rows": [],
    },
}


def _fallback_rows(name: str) -> list[dict]:
    rows: list[dict] = []
    for lo, hi, factor in _MULTIFAMILY_FACTORS:
        label = f"{lo}" if lo == hi else f"{lo}-{hi}"
        rows.append({"units": label, "factor": f"{factor * 100:.0f}%"})
    rows.append({"units": "62+", "factor": "23%"})
    return rows


_TABLE_FALLBACKS["220.84"]["rows"] = _fallback_rows("220.84")


def seed_nec_tables(db: Session) -> int:
    data = [(name, meta["description"], meta["rows"]) for name, meta in _TABLE_FALLBACKS.items()]
    inserted = 0
    for name, desc, rows in data:
        if db.query(NECTable).filter(NECTable.name == name).first():
            continue
        db.add(NECTable(name=name, description=desc, rows=rows))
        inserted += 1
    db.commit()
    return inserted


def load_text() -> str:
    global _text_cache
    if _text_cache is not None:
        return _text_cache
    # try DB first
    try:
        db = SessionLocal()
        rows = db.query(NECChunk).order_by(NECChunk.chunk_index).all()
        db.close()
        if rows:
            _text_cache = "\n\n".join(r.content for r in rows)
            return _text_cache
    except Exception as e:
        print("NEC DB load failed:", e)
    # fallback to file
    _text_cache = _read_file()
    return _text_cache


def invalidate_cache():
    global _text_cache
    _text_cache = None
    _coverage_cache.clear()


router = APIRouter(prefix="/nec", tags=["nec-reference"])


@router.get("/content")
def content(offset: int = 0, limit: int = 5000, user=Depends(get_current_user)):
    text = load_text()
    if not text:
        return {"offset": offset, "limit": limit, "total": 0, "text": "", "error": "NEC text not loaded"}
    total = len(text)
    return {"offset": offset, "limit": limit, "total": total, "text": text[offset:offset + limit]}


def _snippet(source: str, needle: str, radius: int = 240) -> str:
    """Build an HTML-safe snippet with the match highlighted."""
    idx = source.lower().find(needle.lower())
    if idx < 0:
        raw = source[: radius * 2]
        prefix = ""
        suffix = "…" if len(source) > len(raw) else ""
    else:
        start = max(0, idx - radius)
        end = min(len(source), idx + len(needle) + radius * 2)
        raw = source[start:end]
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(source) else ""
    text = html.escape(re.sub(r"\s+", " ", raw).strip())
    if needle:
        text = re.sub(re.escape(html.escape(needle)), lambda m: f"<mark>{m.group(0)}</mark>", text, flags=re.IGNORECASE)
    return prefix + text + suffix


def _search_file(q: str, limit: int) -> dict:
    text = load_text()
    if not text:
        return {"query": q, "results": [], "count": 0, "error": "NEC text not loaded"}
    low = text.lower()
    needle = q.lower()
    positions = []
    start = 0
    while True:
        idx = low.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + len(needle)
    results = [{"position": idx, "snippet": _snippet(text[idx - 40:idx + len(q) + 600], q, radius=240)} for idx in positions[:limit]]
    return {"query": q, "count": len(positions), "results": results}


@router.get("/search")
def search(
    q: str = Query(..., min_length=2),
    article: str | None = None,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total = db.query(NECChunk).count()
    if total == 0:
        return _search_file(q, limit)

    escaped = q.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    query = db.query(NECChunk).filter(NECChunk.content.ilike(f"%{escaped}%", escape="\\"))
    if article:
        query = query.filter(NECChunk.article == article)
    count = query.count()

    candidates = query.order_by(NECChunk.chunk_index).limit(500).all()
    needle = q.lower()

    def score(chunk: NECChunk) -> float:
        hits = chunk.content.lower().count(needle)
        bonus = _ARTICLE_BOOST.get(chunk.article or "", 0)
        section = chunk.section or ""
        if section:
            if q == section or q.startswith((section + "(", section + " ")):
                bonus += 10
            elif section in q:
                bonus += 4
        return min(hits, 5) + bonus

    candidates.sort(key=lambda c: (-score(c), c.chunk_index))
    page = candidates[offset: offset + limit]
    results = [
        {
            "chunk_index": c.chunk_index,
            "article": c.article,
            "section": c.section,
            "title": c.title,
            "section_title": c.section_title,
            "snippet": _snippet(c.content, q),
        }
        for c in page
    ]
    return {"query": q, "article": article, "count": count, "results": results, "offset": offset, "limit": limit}


@router.get("/status")
def status(user=Depends(get_current_user), db: Session = Depends(get_db)):
    chunks = db.query(NECChunk).count()
    db_chars = db.query(func.coalesce(func.sum(func.length(NECChunk.content)), 0)).scalar() or 0
    articles = db.query(func.count(func.distinct(NECChunk.article))).scalar() or 0
    sections = db.query(func.count(func.distinct(NECChunk.section))).scalar() or 0
    info = _coverage_cache.get(chunks)
    if info is None:
        source = _read_file()
        rows = db.query(NECChunk.content).order_by(NECChunk.chunk_index).all() if chunks else []
        info = {
            "source_chars": len(source),
            "db_chars": db_chars,
            "coverage": round(coverage(source, [{"content": r[0]} for r in rows]), 4) if source else 0.0,
        }
        if chunks:
            _coverage_cache[chunks] = info
    return {
        "chunker_version": CHUNKER_VERSION,
        "source_file": NEC_PATH,
        "chunks": chunks,
        "articles": articles,
        "sections": sections,
        **info,
    }


@router.get("/articles")
def list_articles(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(
        NECChunk.article,
        NECChunk.title,
        NECChunk.section,
        func.count(NECChunk.id).label("chunks"),
        func.coalesce(func.sum(func.length(NECChunk.content)), 0).label("chars"),
    ).group_by(NECChunk.article, NECChunk.title, NECChunk.section).all()

    merged: dict[str, dict] = {}
    for article, title, section, chunks, chars in rows:
        if not article:
            continue
        entry = merged.setdefault(article, {"article": article, "title": title, "sections": set(), "chunks": 0, "chars": 0})
        if not entry["title"] and title:
            entry["title"] = title
        if section:
            entry["sections"].add(section)
        entry["chunks"] += chunks
        entry["chars"] += chars
    result = []
    for entry in sorted(merged.values(), key=lambda e: article_sort_key(e["article"])):
        entry["sections"] = len(entry["sections"])
        result.append(entry)
    return result


@router.get("/articles/{article}")
def get_article(article: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(NECChunk).filter(NECChunk.article == article).order_by(NECChunk.chunk_index).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Article not found")
    sections: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        if row.section and row.section not in seen:
            seen.add(row.section)
            sections.append({"section": row.section, "title": row.section_title})
    return {
        "article": article,
        "title": rows[0].title,
        "chunks": len(rows),
        "chars": sum(len(r.content) for r in rows),
        "sections": sections,
        "text": "\n".join(r.content for r in rows),
    }


@router.get("/sections/{section}")
def get_section(section: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(NECChunk).filter(NECChunk.section == section).order_by(NECChunk.chunk_index).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Section not found")
    return {
        "section": section,
        "title": rows[0].section_title,
        "article": rows[0].article,
        "text": "\n".join(r.content for r in rows),
    }


@router.post("/seed")
def seed_endpoint(force: bool = False, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = seed_nec_chunks(db, force=force)
    invalidate_cache()
    return {"inserted": n, "total_chunks": db.query(NECChunk).count()}


def _table_from_db(name: str, db: Session):
    row = db.query(NECTable).filter(NECTable.name == name).first()
    if row:
        return {"table": row.name, "description": row.description, "rows": row.rows}
    return None


@router.get("/tables")
def list_tables(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(NECTable).order_by(NECTable.name).all()
    return [{"table": r.name, "description": r.description} for r in rows]


@router.get("/tables/{name}")
def table_by_name(name: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = _table_from_db(name, db)
    if row:
        return row
    fallback = _TABLE_FALLBACKS.get(name)
    if fallback:
        return {"table": name, "description": fallback["description"], "rows": fallback["rows"]}
    raise HTTPException(status_code=404, detail="Table not found")
