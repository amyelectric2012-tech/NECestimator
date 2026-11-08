import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import SessionLocal, get_db
from app.models import NECChunk, NECTable

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


def seed_nec_tables(db) -> int:
    data = [
        ("220.42", "Lighting Load Demand Factors (Dwelling units)",
         [{"portion": "First 3000 VA", "factor": "100%"}, {"portion": "3001 to 120,000 VA", "factor": "35%"}, {"portion": "Remainder over 120,000 VA", "factor": "25%"}]),
        ("220.54", "Demand Factors for Household Electric Clothes Dryers",
         [{"dryers": "1-4", "factor": "100%"}, {"dryers": "5", "factor": "85%"}, {"dryers": "6", "factor": "75%"}, {"dryers": "7", "factor": "65%"}, {"dryers": "8", "factor": "60%"}, {"dryers": "9", "factor": "55%"}, {"dryers": "10", "factor": "50%"}, {"dryers": "11", "factor": "47%"}, {"dryers": "12-23", "factor": "47% - 1%/dryer over 11"}, {"dryers": "24-42", "factor": "35% - 0.5%/dryer over 23"}, {"dryers": "43+", "factor": "25%"}]),
        ("220.55", "Demand Factors and Loads for Household Electric Ranges (Column C, not over 12 kW)",
         [{"ranges": n, "max_demand_kw": v} for n, v in {1:8,2:11,3:14,4:17,5:20,6:21,7:22,8:23,9:24,10:25,11:26,12:27,13:28,14:29,15:30,16:31,17:32,18:33,19:34,20:35,21:36,22:37,23:38,24:39,25:40}.items()]),
        ("220.84", "Optional Calculations — Demand Factors for Three or More Multifamily Dwelling Units",
         [{"units": "3-5", "factor": "45%"}, {"units": "6-7", "factor": "44%"}, {"units": "8-10", "factor": "43%"}, {"units": "11-13", "factor": "42%"}, {"units": "14-16", "factor": "41%"}, {"units": "17-19", "factor": "40%"}, {"units": "20-22", "factor": "39%"}, {"units": "23-25", "factor": "38%"}, {"units": "26-28", "factor": "37%"}, {"units": "29-31", "factor": "36%"}, {"units": "32-34", "factor": "35%"}, {"units": "35-37", "factor": "34%"}, {"units": "38-40", "factor": "33%"}, {"units": "41-43", "factor": "32%"}, {"units": "44-46", "factor": "31%"}, {"units": "47-49", "factor": "30%"}, {"units": "50-52", "factor": "29%"}, {"units": "53-55", "factor": "28%"}, {"units": "56-58", "factor": "27%"}, {"units": "59-61", "factor": "26%"}, {"units": "62+", "factor": "23%"}]),
    ]
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
    r = _table_from_db(name, db)
    if r: return r
    raise HTTPException(status_code=404, detail="Table not found")


@router.get("/tables/220.42")
def table_220_42(user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = _table_from_db("220.42", db)
    if r: return r
    return {"table": "220.42", "description": "Lighting Load Demand Factors (Dwelling units)",
            "rows": [
                {"portion": "First 3000 VA", "factor": "100%"},
                {"portion": "3001 to 120,000 VA", "factor": "35%"},
                {"portion": "Remainder over 120,000 VA", "factor": "25%"},
            ]}


@router.get("/tables/220.54")
def table_220_54(user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = _table_from_db("220.54", db)
    if r: return r
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
def table_220_55(user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = _table_from_db("220.55", db)
    if r: return r
    return {"table": "220.55", "description": "Demand Factors and Loads for Household Electric Ranges (Column C, not over 12 kW)",
            "rows": [{"ranges": n, "max_demand_kw": v} for n, v in {
                1: 8, 2: 11, 3: 14, 4: 17, 5: 20, 6: 21, 7: 22, 8: 23, 9: 24, 10: 25,
                11: 26, 12: 27, 13: 28, 14: 29, 15: 30, 16: 31, 17: 32, 18: 33, 19: 34, 20: 35,
                21: 36, 22: 37, 23: 38, 24: 39, 25: 40,
            }.items()]}


@router.get("/tables/220.84")
def table_220_84(user=Depends(get_current_user), db: Session = Depends(get_db)):
    r = _table_from_db("220.84", db)
    if r: return r
    from app.calculations.nec220 import _MULTIFAMILY_FACTORS
    rows = []
    for lo, hi, f in _MULTIFAMILY_FACTORS:
        label = f"{lo}" if lo == hi else f"{lo}-{hi}"
        rows.append({"units": label, "factor": f"{f*100:.0f}%"})
    rows.append({"units": "62+", "factor": "23%"})
    return {"table": "220.84", "description": "Optional Calculations — Demand Factors for Three or More Multifamily Dwelling Units", "rows": rows}
