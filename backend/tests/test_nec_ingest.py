import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient

from app.main import app
from app.routers.nec_reference import _snippet
from app.services.nec_ingest import MAX_CHARS, article_list, build_chunks, coverage, read_source

client = TestClient(app)

SYNTHETIC = """NFPA 70 front matter
ARTICLE 90
Introduction
90.1 Purpose.
This Code is not intended as a design specification.
ARTICLE 220
Branch-Circuit, Feeder, and Service Load Calculations
220.42 General Lighting.
The demand factors specified in Table 220.42 shall apply.
220.55 Demand Factors for Ranges.
Table 220.55 gives the demand factors.
INFORMATIVE ANNEX D
Examples
Example D1(a) covers a dwelling unit.
Index
Lighting, 220.42
"""


def test_build_chunks_preserves_text_and_metadata():
    chunks = build_chunks(SYNTHETIC)
    assert coverage(SYNTHETIC, chunks) == 1.0
    articles = article_list(chunks)
    assert "90" in articles and "220" in articles and "annex-D" in articles and "index" in articles
    lighting = [c for c in chunks if c["section"] == "220.42"]
    assert lighting and lighting[0]["section_title"] == "General Lighting"
    assert "Branch-Circuit, Feeder, and Service Load Calculations" in lighting[0]["title"]
    assert all(len(c["content"]) <= MAX_CHARS for c in chunks)


def test_full_nec_text_is_fully_ingested():
    source = read_source()
    assert len(source) > 4_000_000
    chunks = build_chunks(source)
    assert len(chunks) > 1500
    assert coverage(source, chunks) > 0.9999
    articles = set(article_list(chunks))
    for expected in ("90", "110", "210", "220", "250", "400", "690", "840"):
        assert expected in articles
    assert "annex-D" in articles and "index" in articles and "chapter-9" in articles
    assert max(len(c["content"]) for c in chunks) <= MAX_CHARS
    section = [c for c in chunks if c["section"] == "220.42"]
    assert section and section[0]["article"] == "220"


def _token() -> dict:
    client.post("/auth/register", json={"email": "nec@test.com", "password": "pw123"})
    r = client.post("/auth/login", json={"email": "nec@test.com", "password": "pw123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_nec_status_articles_and_tables():
    h = _token()
    r = client.get("/nec/status", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["source_chars"] > 4_000_000
    assert body["chunker_version"] >= 2

    r = client.get("/nec/articles", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = client.get("/nec/tables/220.42", headers=h)
    assert r.status_code == 200
    assert len(r.json()["rows"]) == 3

    r = client.get("/nec/tables/999.99", headers=h)
    assert r.status_code == 404

    r = client.get("/nec/sections/220.42", headers=h)
    assert r.status_code == 404


def test_nec_search_uses_file_fallback_and_highlights():
    h = _token()
    r = client.get("/nec/search?q=grounding&limit=3", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert len(body["results"]) <= 3
    assert "<mark>" in body["results"][0]["snippet"]


def test_snippet_escapes_html():
    snippet = _snippet("<script>alert(1)</script> 220.42", "script")
    assert "<script>" not in snippet
    assert "&lt;" in snippet
    assert "<mark>" in snippet
