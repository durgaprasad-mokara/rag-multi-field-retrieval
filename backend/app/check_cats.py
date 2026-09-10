from app.database import SessionLocal
from app.models import Category, DocumentType

def check():
    db = SessionLocal()
    cats = db.query(Category).all()
    print("Categories:", len(cats))
    types = db.query(DocumentType).all()
    print("Types:", len(types))
    
    types_named = db.query(DocumentType).filter(DocumentType.name == "Technology Articles").all()
    print("Number of 'Technology Articles' types:", len(types_named))
    for dt in types_named:
        print("  - Type ID:", dt.id, "Category ID:", dt.category_id)
    pass
    print("Type's actual category_id:", dt.category_id if dt else "None")
    
if __name__ == "__main__":
    check()
