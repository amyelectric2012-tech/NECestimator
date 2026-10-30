import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import Base, SessionLocal, engine
from app.models import NECChunk
from app.routers.nec_reference import seed_nec_chunks

Base.metadata.create_all(bind=engine)
db = SessionLocal()
n = seed_nec_chunks(db)
print(f"NEC chunks inserted: {n} (total {db.query(NECChunk).count()})")
db.close()
