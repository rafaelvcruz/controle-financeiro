from datetime import date
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (CheckConstraint("closing_day BETWEEN 1 AND 31", name="ck_card_closing_day"), CheckConstraint("due_day BETWEEN 1 AND 31", name="ck_card_due_day"), CheckConstraint("credit_limit > 0", name="ck_card_limit_positive"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(40))
    last_four: Mapped[str | None] = mapped_column(String(4))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    closing_day: Mapped[int] = mapped_column(nullable=False)
    due_day: Mapped[int] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    purchases: Mapped[list["CardPurchase"]] = relationship(back_populates="card", cascade="all, delete-orphan")

class CardPurchase(Base):
    __tablename__ = "card_purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("credit_cards.id"), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    installments_count: Mapped[int] = mapped_column(nullable=False, default=1)
    subgroup_id: Mapped[int | None] = mapped_column(ForeignKey("subgroups.id"))
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    card: Mapped[CreditCard] = relationship(back_populates="purchases")
    installments: Mapped[list["CardInstallment"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")

class CardInstallment(Base):
    __tablename__ = "card_installments"
    __table_args__ = (UniqueConstraint("purchase_id", "installment_number", name="uq_purchase_installment"), CheckConstraint("amount > 0", name="ck_installment_amount_positive"))
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("card_purchases.id", ondelete="CASCADE"), nullable=False)
    installment_number: Mapped[int] = mapped_column(nullable=False)
    invoice_month: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    purchase: Mapped[CardPurchase] = relationship(back_populates="installments")

class CardPayment(Base):
    __tablename__ = "card_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("credit_cards.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    invoice_month: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))
