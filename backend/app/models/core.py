from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Date, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accounts: Mapped[list["FinancialAccount"]] = relationship(back_populates="person")

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("nature IN ('RECEITA','DESPESA','INVESTIMENTO','MISTA')", name="ck_category_nature"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nature: Mapped[str] = mapped_column(String(20), nullable=False, default="MISTA")
    suggested_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    groups: Mapped[list["Group"]] = relationship(back_populates="category")

class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_group_category_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[Category] = relationship(back_populates="groups")
    subgroups: Mapped[list["Subgroup"]] = relationship(back_populates="group")

class Subgroup(Base):
    __tablename__ = "subgroups"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_subgroup_group_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    group: Mapped[Group] = relationship(back_populates="subgroups")

class FinancialAccount(Base):
    __tablename__ = "financial_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    balance_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    person: Mapped[Person | None] = relationship(back_populates="accounts")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
