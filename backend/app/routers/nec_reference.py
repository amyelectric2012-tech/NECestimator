import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import SessionLocal, get_db
from app.models import NECChunk

NEC_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nec_2017.txt")
if not os.path.exists(NEC_PATH):
    NEC_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "data", "nec_2017.txt")
if not os.path.exists(NEC_PATH):
    NEC_PATH = "/home/amram/NECestimator/backend/data/nec_2017.txt"

_text_cache = None


def _read_file() -> str:
    try:
        with open(NEC_PATH, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def seed_nec_chunks(db: Session | None = None, chunk_size: int = 4000) -> int:
    """Ingest the full NEC 2017 text into nec_chunks if empty. Returns number inserted."""
    own = db is None
    if own:
        db = SessionLocal()
    try:
        if db.query(NECChunk).count() > 0:
            return 0
        text = _read_file()
        if not text:
            return 0
        # fixed-size chunks, break at newline when possible
        chunks = []
        i = 0
        n = len(text)
        while i < n:
            end = min(i + chunk_size, n)
            if end < n:
                nl = text.rfind(chr(10), i, end)
                if nl > i + chunk_size // 2:
                    end = nl + 1
            chunks.append(text[i:end].strip())
            i = end
        chunks = [c for c in chunks if c]
        for i, c in enumerate(chunks):
            db.add(NECChunk(chunk_index=i, content=c))
        db.commit()
        return len(chunks)
    finally:
        if own:
            db.close()


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


router = APIRouter(prefix="/nec", tags=["nec-reference"])


@router.get("/content")
def content(offset: int = 0, limit: int = 5000, user=Depends(get_current_user)):
    text = load_text()
    if not text:
        return {"offset": offset, "limit": limit, "total": 0, "text": "", "error": "NEC text not loaded"}
    total = len(text)
    chunk = text[offset:offset + limit]
    return {"offset": offset, "limit": limit, "total": total, "text": chunk}


@router.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = 10, user=Depends(get_current_user)):
    text = load_text()
    if not text:
        return {"query": q, "results": [], "error": "NEC text not loaded"}
    low = text.lower()
    needle = q.lower()
    positions = []
    start = 0
    while True:
        idx = low.find(needle, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + len(q)
    import re as _re
    results = []
    for idx in positions[:limit]:
        s = max(0, idx - 240)
        e = min(len(text), idx + len(q) + 480)
        snippet = text[s:e].replace("\n", " ")
        snippet = _re.sub(r"\s{2,}", " ", snippet)
        def _hl(m):
            return f"<mark>{m.group(0)}</mark>"
        snippet = _re.sub(_re.escape(q), _hl, snippet, flags=_re.IGNORECASE)
        prefix = "…" if s > 0 else ""
        suffix = "…" if e < len(text) else ""
        results.append({"position": idx, "snippet": prefix + snippet + suffix})
    return {"query": q, "count": len(positions), "results": results}


@router.post("/seed")
def seed_endpoint(user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = seed_nec_chunks(db)
    invalidate_cache()
    return {"inserted": n, "total_chunks": db.query(NECChunk).count()}


@router.get("/tables/220.42")
def table_220_42(user=Depends(get_current_user)):
    return {"table": "220.42", "description": "Lighting Load Demand Factors (Dwelling units)",
            "rows": [
                {"portion": "First 3000 VA", "factor": "100%"},
                {"portion": "3001 to 120,000 VA", "factor": "35%"},
                {"portion": "Remainder over 120,000 VA", "factor": "25%"},
            ]}


@router.get("/tables/220.54")
def table_220_54(user=Depends(get_current_user)):
    return {"table": "220.54", "description": "Demand Factors for Household Electric Clothes Dryers",
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
            ]}


@router.get("/tables/220.55")
def table_220_55(user=Depends(get_current_user)):
    return {"table": "220.55", "description": "Demand Factors and Loads for Household Electric Ranges (Column C, not over 12 kW)",
            "rows": [{"ranges": n, "max_demand_kw": v} for n, v in {
                1: 8, 2: 11, 3: 14, 4: 17, 5: 20, 6: 21, 7: 22, 8: 23, 9: 24, 10: 25,
                11: 26, 12: 27, 13: 28, 14: 29, 15: 30, 16: 31, 17: 32, 18: 33, 19: 34, 20: 35,
                21: 36, 22: 37, 23: 38, 24: 39, 25: 40,
            }.items()]}


@router.get("/tables/220.84")
def table_220_84(user=Depends(get_current_user)):
    from app.calculations.nec220 import _MULTIFAMILY_FACTORS
    rows = []
    for lo, hi, f in _MULTIFAMILY_FACTORS:
        label = f"{lo}" if lo == hi else f"{lo}-{hi}"
        rows.append({"units": label, "factor": f"{f*100:.0f}%"})
    rows.append({"units": "62+", "factor": "23%"})
    return {"table": "220.84", "description": "Optional Calculations — Demand Factors for Three or More Multifamily Dwelling Units", "rows": rows}
