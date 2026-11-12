import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import Base, SessionLocal, engine
from app.models import NECChunk
from app.routers.nec_reference import seed_nec_chunks
from app.services.nec_ingest import build_chunks, coverage, read_source

force = "--force" in sys.argv
Base.metadata.create_all(bind=engine)
db = SessionLocal()
n = seed_nec_chunks(db, force=force)
chunks = build_chunks(read_source())
print(f"NEC chunks inserted: {n} (total {db.query(NECChunk).count()})")
print(f"Coverage of source text: {coverage(read_source(), chunks) * 100:.2f}%")
db.close()
