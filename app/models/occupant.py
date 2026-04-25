# stdlib
from datetime import date, datetime
from uuid import UUID

# third-party
from sqlmodel import Field, SQLModel

# local
from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class OccupantBase(SQLModel):
    full_name: str = Field(
        max_length=200,
        description="Full name của occupant, NOT NULL",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="nullable, optional cho PATCH",
    )
    id_card_number: str | None = Field(
        default=None,
        max_length=20,
        description="Số CCCD/CMND của occupant, nullable (không bắt buộc)",
    )
    birth_date: date | None = Field(
        default=None,
        description="Ngày sinh của occupant, nullable",
    )
    relationship: str | None = Field(
        default=None, max_length=50, description="free text: 'vợ', 'con', 'bạn'"
    )
    note: str | None = Field(
        default=None,
        description="Landlord internal note về tenant, nullable",
    )


class Occupant(OccupantBase, TimestampMixin, UUIDPrimaryKeyMixin, table=True):
    """`occupants` table — thông tin occupant + lifecycle fields."""

    __tablename__ = "occupants"

    moved_in_date: date = Field(
        default_factory=date.today,
        description="Ngày thực tế occupant đến ở, not null)",
    )
    moved_out_date: date | None = Field(default=None, description=" Ngày occupant dọn đi")
    tenant_id: UUID = Field(
        foreign_key="tenants.id", description="Tenant đại diện cho occupant ở cùng"
    )


class OccupantCreate(OccupantBase):
    pass


class OccupantRead(OccupantBase):
    id: UUID
    tenant_id: UUID  # cần để client biết Occupant thuộc Tenant nào
    moved_in_date: date
    moved_out_date: date | None
    created_at: datetime
    updated_at: datetime


class OccupantUpdate(SQLModel):
    full_name: str | None = Field(
        default=None,
        max_length=200,
        description="Full name của occupant, NOT NULL",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Phone number của occupant, NOT NULL",
    )
    id_card_number: str | None = Field(
        default=None,
        max_length=20,
        description="Số CCCD/CMND của occupant, nullable (không bắt buộc)",
    )
    birth_date: date | None = Field(
        default=None,
        description="Ngày sinh của occupant, nullable",
    )
    relationship: str | None = Field(
        default=None, max_length=50, description='free text: "vợ", "con", "bạn"'
    )

    note: str | None = Field(
        default=None,
        description="Landlord internal note về tenant, nullable",
    )
