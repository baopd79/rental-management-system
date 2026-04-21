"""Smoke test — verify DB schema works end-to-end với SQLModel."""

import os
from dotenv import load_dotenv
from sqlmodel import Session, create_engine, select
from app.models import User, Property
from app.core.enums import UserRole

load_dotenv()

DB_URL = (
    f"postgresql+psycopg://"
    f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}"
    f"/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(DB_URL, echo=False)


def test_user_crud():
    """Insert landlord → read back → delete."""
    with Session(engine) as session:
        # Create
        landlord = User(
            email="smoke_test@rms.local",
            password_hash="dummy",
            full_name="Smoke Test Landlord",
            role=UserRole.LANDLORD,
        )
        session.add(landlord)
        session.commit()
        session.refresh(landlord)
        assert landlord.id is not None
        print(f"✅ Create User: {landlord.id}")

        # Read
        result = session.exec(
            select(User).where(User.email == "smoke_test@rms.local")
        ).one()
        assert result.role == UserRole.LANDLORD, f"Enum mismatch: {result.role}"
        print(f"✅ Read back: role={result.role} ({type(result.role).__name__})")

        # Create Property với FK
        prop = Property(
            landlord_id=landlord.id,
            name="Smoke Test Property",
            address="Test Address",
            billing_day=1,
        )
        session.add(prop)
        session.commit()
        session.refresh(prop)
        print(f"✅ Create Property with FK: {prop.id}")

        # Cleanup
        session.delete(prop)
        session.delete(result)
        session.commit()
        print("✅ Cleanup OK")


if __name__ == "__main__":
    test_user_crud()
    print("\n🎉 Smoke test passed")
