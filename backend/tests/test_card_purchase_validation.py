import unittest
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.routes import card_purchase_create, card_purchase_update
from app.db.base import Base
from app.models import CardInstallment, Category, CreditCard, Group, Subgroup
from app.schemas.core import CardPurchaseIn


class CardPurchaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        expense = Category(name="Despesas", nature="DESPESA")
        income = Category(name="Receitas", nature="RECEITA")
        self.db.add_all([expense, income])
        self.db.flush()

        expense_group = Group(category_id=expense.id, name="Casa")
        income_group = Group(category_id=income.id, name="Renda")
        self.db.add_all([expense_group, income_group])
        self.db.flush()

        self.expense_subgroup = Subgroup(group_id=expense_group.id, name="Mercado")
        self.income_subgroup = Subgroup(group_id=income_group.id, name="Salário")
        self.card = CreditCard(
            name="Cartão",
            credit_limit=Decimal("1000.00"),
            closing_day=10,
            due_day=20,
        )
        self.db.add_all([self.expense_subgroup, self.income_subgroup, self.card])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def purchase_payload(self, **overrides):
        values = {
            "card_id": self.card.id,
            "purchase_date": date(2026, 11, 1),
            "description": "Compra de teste",
            "total_amount": Decimal("10.00"),
            "installments_count": 1,
        }
        values.update(overrides)
        return CardPurchaseIn(**values)

    def test_installments_preserve_total_cents_and_reject_zero_value_parts(self):
        purchase = card_purchase_create(
            self.purchase_payload(
                total_amount=Decimal("0.07"),
                installments_count=3,
                subgroup_id=self.expense_subgroup.id,
            ),
            self.db,
        )
        amounts = list(
            self.db.scalars(
                select(CardInstallment.amount)
                .where(CardInstallment.purchase_id == purchase.id)
                .order_by(CardInstallment.installment_number)
            )
        )
        self.assertEqual(amounts, [Decimal("0.03"), Decimal("0.02"), Decimal("0.02")])

        invalid_payload = self.purchase_payload(
            total_amount=Decimal("0.02"),
            installments_count=3,
        )
        with self.assertRaises(HTTPException) as error:
            card_purchase_create(invalid_payload, self.db)
        self.assertEqual(error.exception.status_code, 422)

        with self.assertRaises(HTTPException) as error:
            card_purchase_update(purchase.id, invalid_payload, self.db)
        self.assertEqual(error.exception.status_code, 422)

    def test_card_purchase_rejects_income_categories_on_create_and_update(self):
        invalid_payload = self.purchase_payload(subgroup_id=self.income_subgroup.id)
        with self.assertRaises(HTTPException) as error:
            card_purchase_create(invalid_payload, self.db)
        self.assertEqual(error.exception.status_code, 422)

        purchase = card_purchase_create(self.purchase_payload(), self.db)
        with self.assertRaises(HTTPException) as error:
            card_purchase_update(purchase.id, invalid_payload, self.db)
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
