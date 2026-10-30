import os

from fastapi import APIRouter, Depends, Query

from app.auth.deps import get_current_user

NEC_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "(NFPA) National Fire Protection Association-National Electrical Code 2017.txt")
# fallback absolute
if not os.path.exists(NEC_PATH):
    NEC_PATH = "/home/amram/NECestimator/(NFPA) National Fire Protection Association-National Electrical Code 2017.txt"

_text_cache = None


def load_text():
    global _text_cache
    if _text_cache is None:
        try:
            with open(NEC_PATH, "r", encoding="utf-8", errors="ignore") as f:
                _text_cache = f.read()
        except Exception:
            _text_cache = ""
    return _text_cache


router = APIRouter(prefix="/nec", tags=["nec-reference"])


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
    results = []
    for idx in positions[:limit]:
        s = max(0, idx - 200)
        e = min(len(text), idx + len(q) + 400)
        snippet = text[s:e].replace("\n", " ")
        snippet = snippet.replace(q, f"**{q}**") if q in snippet else snippet
        results.append({"position": idx, "snippet": snippet})
    return {"query": q, "count": len(positions), "results": results}


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
