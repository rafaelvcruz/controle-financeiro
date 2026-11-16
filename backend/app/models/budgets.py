from datetime import date
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("reference_month", name="uq_budget_reference_month"),
        CheckConstraint("status IN ('ABERTO','ENCERRADO')", name="ck_budget_status"),
        CheckConstraint("reference_income >= 0", name="ck_budget_income_nonnegative"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reference_month: Mapped[date] = mapped_column(Date, nullable=False)  # sempre primeiro dia do mês
    description: Mapped[str] = mapped_column(String(120), nullable=False, default="Orçamento mensal")
    reference_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ABERTO")
    items: Mapped[list["BudgetItem"]] = relationship(back_populates="budget", cascade="all, delete-orphan")

class BudgetItem(Base):
    __tablename__ = "budget_items"
    __table_args__ = (
        UniqueConstraint("budget_id", "category_id", name="uq_budget_item_category"),
        CheckConstraint("planned_amount >= 0", name="ck_budget_item_amount_nonnegative"),
        CheckConstraint("planned_percentage IS NULL OR (planned_percentage >= 0 AND planned_percentage <= 100)", name="ck_budget_item_percentage_range"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    planned_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(String(300))
    budget: Mapped[Budget] = relationship(back_populates="items")
