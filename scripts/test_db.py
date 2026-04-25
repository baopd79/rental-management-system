from sqlmodel import Session, text
from app.db.session import engine

with Session(engine) as s:
    result = s.exec(text("SELECT 1")).first()
    print("DB OK:", result)