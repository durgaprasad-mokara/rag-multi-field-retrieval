from app.api.debug import inspect_document
from app.database import SessionLocal
from uuid import UUID

db = SessionLocal()
try:
    doc_id = UUID("6ac4ba08-a33b-45a5-b86e-d9bae8bead27")
    res = inspect_document(doc_id, db)
    print(res)
finally:
    db.close()
