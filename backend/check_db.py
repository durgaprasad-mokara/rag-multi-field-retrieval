import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DIRECT_URL'])
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public'"))
    for r in res:
        print(f"{r.table_name}.{r.column_name}: {r.data_type}")
