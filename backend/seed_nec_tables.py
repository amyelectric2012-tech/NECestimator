import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import Base, SessionLocal, engine
from app.models import NECTable
from app.routers.nec_reference import seed_nec_tables

Base.metadata.create_all(bind=engine)
db = SessionLocal()
n = seed_nec_tables(db)
print(f"NEC tables inserted: {n} (total {db.query(NECTable).count()})")
db.close()
