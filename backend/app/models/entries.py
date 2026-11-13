from datetime import date
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class FinancialEntry(Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("entry_type IN ('RECEITA','DESPESA','INVESTIMENTO')", name="ck_entry_type"),
        CheckConstraint("status IN ('PREVISTO','REALIZADO','CANCELADO')", name="ck_entry_status"),
        CheckConstraint("amount > 0", name="ck_entry_amount_positive"),
        Index("ix_entry_date_status", "movement_date", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    competence_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    subgroup_id: Mapped[int | None] = mapped_column(ForeignKey("subgroups.id"))
    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.id"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REALIZADO")
    notes: Mapped[str | None] = mapped_column(Text)

class AccountTransfer(Base):
    __tablename__ = "account_transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transfer_amount_positive"),
        CheckConstraint("from_account_id <> to_account_id", name="ck_transfer_different_accounts"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    to_account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REALIZADO")
    description: Mapped[str] = mapped_column(String(180), nullable=False, default="Transferência entre contas")
