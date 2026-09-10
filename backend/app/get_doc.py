from app.database import engine
from sqlalchemy import text
with engine.connect() as c:
    r = c.execute(text("SELECT content FROM document_chunks WHERE document_id = '6ac4ba08-a33b-45a5-b86e-d9bae8bead27'"))
    for row in r.fetchall():
        print(row[0])
        print("---")
