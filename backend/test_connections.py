import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from qdrant_client import QdrantClient

# Load the .env file explicitly
load_dotenv()

print("==================================================")
print("🚀 TESTING EXTERNAL CONNECTIONS")
print("==================================================")

# 1. Test PostgreSQL
db_url = os.getenv("DATABASE_URL")
print(f"\nTesting PostgreSQL Connection...")
if db_url and "[YOUR-PASSWORD]" in db_url:
    print("⚠️ WARNING: You still have '[YOUR-PASSWORD]' in your DATABASE_URL.")
    print("Please replace it with your actual Supabase password in the .env file.")
else:
    try:
        engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        connection = engine.connect()
        connection.close()
        print("✅ Successfully connected to PostgreSQL!")
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")

# 2. Test Qdrant
qdrant_url = os.getenv("QDRANT_URL")
print(f"\nTesting Qdrant Connection... (URL: {qdrant_url})")
try:
    client = QdrantClient(url=qdrant_url, timeout=5)
    collections = client.get_collections()
    print("✅ Successfully connected to Qdrant!")
    print(f"   Collections available: {[c.name for c in collections.collections]}")
except Exception as e:
    print(f"❌ Failed to connect to Qdrant: {e}")
