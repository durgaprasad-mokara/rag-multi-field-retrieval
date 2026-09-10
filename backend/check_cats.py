import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

from app.database import SessionLocal
from app.models import Category, DocumentType

def check():
    db = SessionLocal()
    cats = db.query(Category).all()
    print("Categories:", len(cats))
    types = db.query(DocumentType).all()
    print("Types:", len(types))
    
    if types:
        print("Sample Type:")
        print("  id:", types[0].id)
        print("  category_id:", types[0].category_id)
        print("  name:", types[0].name)
    
if __name__ == "__main__":
    check()
