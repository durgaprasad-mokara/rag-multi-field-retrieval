from app.database import engine
from sqlalchemy import text
with engine.connect() as c:
    r = c.execute(text("SELECT id, document_name FROM documents WHERE document_name LIKE '%Mokara_Durga_Prasad.pdf%'"))
    print(r.fetchall())
