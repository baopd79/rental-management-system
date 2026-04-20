"""
ServiceRoom junction table — Nhóm 5.

Khi Service.scope = selected_rooms, cần biết service áp dụng cho Room nào.
Khi Service.scope = all_rooms, junction KHÔNG cần — query tất cả rooms.

Schema:
- Composite primary key (service_id, room_id) — không có UUID PK
- Không có updated_at — junction table thường immutable (add/remove, không edit)
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.base import CreatedAtOnlyMixin


class ServiceRoom(CreatedAtOnlyMixin, SQLModel, table=True):
    """`service_rooms` junction table.

    Composite PK (service_id, room_id) → không dùng UUIDPrimaryKeyMixin.
    Relationship là (service_id, room_id) unique → SQLAlchemy interpret
    cả 2 làm PK composite khi primary_key=True ở cả 2 fields.
    """

    __tablename__ = "service_rooms"

    service_id: UUID = Field(
        foreign_key="services.id",
        primary_key=True,
    )
    room_id: UUID = Field(
        foreign_key="rooms.id",
        primary_key=True,
    )


# Junction table không cần Create/Read/Update schemas.
# Logic "add room to service" hoặc "remove room from service" là
# trực tiếp INSERT/DELETE ở service layer, không qua Pydantic schema.
