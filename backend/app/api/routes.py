from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Person, Category, Group, Subgroup, FinancialAccount
from app.schemas.core import PersonIn, PersonOut, CategoryIn, CategoryOut, GroupIn, GroupOut, SubgroupIn, SubgroupOut, AccountIn, AccountOut

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "controle-financeiro-api"}

def list_items(db, model):
    return list(db.scalars(select(model).order_by(model.id)).all())

def create_item(db, model, payload):
    item = model(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Registro duplicado ou relacionamento inválido.")
    return item

@router.get("/people", response_model=list[PersonOut])
def people_list(db: Session = Depends(get_db)): return list_items(db, Person)
@router.post("/people", response_model=PersonOut, status_code=201)
def people_create(payload: PersonIn, db: Session = Depends(get_db)): return create_item(db, Person, payload)

@router.get("/categories", response_model=list[CategoryOut])
def categories_list(db: Session = Depends(get_db)): return list_items(db, Category)
@router.post("/categories", response_model=CategoryOut, status_code=201)
def categories_create(payload: CategoryIn, db: Session = Depends(get_db)): return create_item(db, Category, payload)

@router.get("/groups", response_model=list[GroupOut])
def groups_list(db: Session = Depends(get_db)): return list_items(db, Group)
@router.post("/groups", response_model=GroupOut, status_code=201)
def groups_create(payload: GroupIn, db: Session = Depends(get_db)):
    if not db.get(Category, payload.category_id): raise HTTPException(404, "Categoria não encontrada.")
    return create_item(db, Group, payload)

@router.get("/subgroups", response_model=list[SubgroupOut])
def subgroups_list(db: Session = Depends(get_db)): return list_items(db, Subgroup)
@router.post("/subgroups", response_model=SubgroupOut, status_code=201)
def subgroups_create(payload: SubgroupIn, db: Session = Depends(get_db)):
    if not db.get(Group, payload.group_id): raise HTTPException(404, "Grupo não encontrado.")
    return create_item(db, Subgroup, payload)

@router.get("/accounts", response_model=list[AccountOut])
def accounts_list(db: Session = Depends(get_db)): return list_items(db, FinancialAccount)
@router.post("/accounts", response_model=AccountOut, status_code=201)
def accounts_create(payload: AccountIn, db: Session = Depends(get_db)):
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    return create_item(db, FinancialAccount, payload)

# Lançamentos e transferências: somente itens REALIZADOS afetam os saldos.
from datetime import date
from decimal import Decimal
from sqlalchemy import func
from app.models import FinancialEntry, AccountTransfer, PaymentMethod
from app.schemas.core import EntryIn, EntryOut, TransferIn, TransferOut, EntryStatusIn

@router.get("/payment-methods")
def payment_methods_list(db: Session = Depends(get_db)):
    return list_items(db, PaymentMethod)

@router.get("/entries", response_model=list[EntryOut])
def entries_list(db: Session = Depends(get_db), start: date | None = None, end: date | None = None, status_filter: str | None = None):
    stmt = select(FinancialEntry).order_by(FinancialEntry.movement_date.desc(), FinancialEntry.id.desc())
    if start: stmt = stmt.where(FinancialEntry.movement_date >= start)
    if end: stmt = stmt.where(FinancialEntry.movement_date <= end)
    if status_filter: stmt = stmt.where(FinancialEntry.status == status_filter)
    return list(db.scalars(stmt).all())

@router.post("/entries", response_model=EntryOut, status_code=201)
def entries_create(payload: EntryIn, db: Session = Depends(get_db)):
    if not db.get(FinancialAccount, payload.account_id): raise HTTPException(404, "Conta financeira não encontrada.")
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    if payload.payment_method_id is not None and not db.get(PaymentMethod, payload.payment_method_id): raise HTTPException(404, "Meio de pagamento não encontrado.")
    if payload.subgroup_id is not None:
        subgroup = db.get(Subgroup, payload.subgroup_id)
        if not subgroup: raise HTTPException(404, "Subgrupo não encontrado.")
        group = db.get(Group, subgroup.group_id)
        category = db.get(Category, group.category_id)
        if category.nature not in ("MISTA", payload.entry_type):
            raise HTTPException(422, "A natureza da categoria não corresponde ao tipo do lançamento.")
    return create_item(db, FinancialEntry, payload)

@router.get("/transfers", response_model=list[TransferOut])
def transfers_list(db: Session = Depends(get_db)):
    return list(db.scalars(select(AccountTransfer).order_by(AccountTransfer.movement_date.desc(), AccountTransfer.id.desc())).all())

@router.post("/transfers", response_model=TransferOut, status_code=201)
def transfers_create(payload: TransferIn, db: Session = Depends(get_db)):
    if payload.from_account_id == payload.to_account_id: raise HTTPException(422, "A conta de origem e destino devem ser diferentes.")
    for account_id in (payload.from_account_id, payload.to_account_id):
        if not db.get(FinancialAccount, account_id): raise HTTPException(404, f"Conta financeira {account_id} não encontrada.")
    return create_item(db, AccountTransfer, payload)


@router.put("/accounts/{account_id}", response_model=AccountOut)
def accounts_update(account_id: int, payload: AccountIn, db: Session = Depends(get_db)):
    item = db.get(FinancialAccount, account_id)
    if not item: raise HTTPException(404, "Conta financeira não encontrada.")
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Não foi possível atualizar a conta.")
    return item

@router.get("/accounts/summary")
def accounts_summary(db: Session = Depends(get_db)):
    accounts = list(db.scalars(select(FinancialAccount).order_by(FinancialAccount.id)).all())
    result = []
    for account in accounts:
        income = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account.id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type == "RECEITA", FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
        expenses = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account.id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type.in_(["DESPESA", "INVESTIMENTO"]), FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
        sent = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.from_account_id == account.id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
        received = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount),  0)).where(AccountTransfer.to_account_id == account.id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
        card_paid = db.scalar(select(func.coalesce(func.sum(CardPayment.amount), 0)).where(CardPayment.account_id == account.id, CardPayment.payment_date >= account.balance_date)) or Decimal("0")
        result.append({"id": account.id, "name": account.name, "account_type": account.account_type, "person_id": account.person_id, "initial_balance": account.initial_balance, "balance_date": account.balance_date, "active": account.active, "balance": account.initial_balance + income + received - expenses - sent - card_paid})
    return result

@router.get("/accounts/{account_id}/balance")
def account_balance(account_id: int, db: Session = Depends(get_db)):
    account = db.get(FinancialAccount, account_id)
    if not account: raise HTTPException(404, "Conta financeira não encontrada.")
    income = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account_id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type == "RECEITA", FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account_id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type.in_(["DESPESA", "INVESTIMENTO"]), FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
    sent = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.from_account_id == account_id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
    received = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.to_account_id == account_id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
    card_paid = db.scalar(select(func.coalesce(func.sum(CardPayment.amount), 0)).where(CardPayment.account_id == account_id, CardPayment.payment_date >= account.balance_date)) or Decimal("0")
    balance = account.initial_balance + income + received - expenses - sent - card_paid
    return {"account_id": account_id, "initial_balance": account.initial_balance, "balance_date": account.balance_date, "balance": balance}

@router.patch("/entries/{entry_id}/status", response_model=EntryOut)
def entries_update_status(entry_id: int, payload: EntryStatusIn, db: Session = Depends(get_db)):
    item = db.get(FinancialEntry, entry_id)
    if not item: raise HTTPException(404, "Lançamento não encontrado.")
    item.status = payload.status
    db.commit(); db.refresh(item)
    return item

@router.put("/entries/{entry_id}", response_model=EntryOut)
def entries_update(entry_id: int, payload: EntryIn, db: Session = Depends(get_db)):
    item = db.get(FinancialEntry, entry_id)
    if not item: raise HTTPException(404, "Lançamento não encontrado.")
    if not db.get(FinancialAccount, payload.account_id): raise HTTPException(404, "Conta financeira não encontrada.")
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    if payload.payment_method_id is not None and not db.get(PaymentMethod, payload.payment_method_id): raise HTTPException(404, "Meio de pagamento não encontrado.")
    if payload.subgroup_id is not None:
        subgroup = db.get(Subgroup, payload.subgroup_id)
        if not subgroup: raise HTTPException(404, "Subgrupo não encontrado.")
        category = db.get(Category, db.get(Group, subgroup.group_id).category_id)
        if category.nature not in ("MISTA", payload.entry_type): raise HTTPException(422, "A natureza da categoria não corresponde ao tipo do lançamento.")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Não foi possível atualizar o lançamento.")
    return item


@router.put("/transfers/{transfer_id}", response_model=TransferOut)
def transfers_update(transfer_id: int, payload: TransferIn, db: Session = Depends(get_db)):
    item = db.get(AccountTransfer, transfer_id)
    if not item: raise HTTPException(404, "Transferência não encontrada.")
    if payload.from_account_id == payload.to_account_id: raise HTTPException(422, "A conta de origem e destino devem ser diferentes.")
    for account_id in (payload.from_account_id, payload.to_account_id):
        if not db.get(FinancialAccount, account_id): raise HTTPException(404, f"Conta financeira {account_id} não encontrada.")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    try:
        db.commit(); db.refresh(item)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Não foi possível atualizar a transferência.")
    return item

# Planejamento orçamentário mensal
from calendar import monthrange
from datetime import date
from sqlalchemy.orm import selectinload
from app.models import Budget, BudgetItem
from app.schemas.core import BudgetIn, BudgetOut


def _validate_budget_payload(payload: BudgetIn, db: Session):
    if payload.reference_month.day != 1:
        raise HTTPException(422, "A data de referência deve ser o primeiro dia do mês.")
    seen = set()
    for item in payload.items:
        if item.category_id in seen:
            raise HTTPException(422, "Uma categoria não pode aparecer duas vezes no mesmo orçamento.")
        seen.add(item.category_id)
        if not db.get(Category, item.category_id):
            raise HTTPException(404, f"Categoria {item.category_id} não encontrada.")


def _budget_query():
    return select(Budget).options(selectinload(Budget.items)).order_by(Budget.reference_month.desc())

@router.get("/budgets", response_model=list[BudgetOut])
def budgets_list(db: Session = Depends(get_db)):
    return list(db.scalars(_budget_query()).all())

@router.post("/budgets", response_model=BudgetOut, status_code=201)
def budgets_create(payload: BudgetIn, db: Session = Depends(get_db)):
    _validate_budget_payload(payload, db)
    data = payload.model_dump()
    items = data.pop("items")
    budget = Budget(**data, items=[BudgetItem(**item) for item in items])
    db.add(budget)
    try:
        db.commit(); db.refresh(budget)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Já existe um orçamento para esse mês ou há uma categoria duplicada.")
    return db.scalar(_budget_query().where(Budget.id == budget.id))

@router.get("/budgets/{budget_id}", response_model=BudgetOut)
def budgets_get(budget_id: int, db: Session = Depends(get_db)):
    budget = db.scalar(_budget_query().where(Budget.id == budget_id))
    if not budget: raise HTTPException(404, "Orçamento não encontrado.")
    return budget

@router.put("/budgets/{budget_id}", response_model=BudgetOut)
def budgets_update(budget_id: int, payload: BudgetIn, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if not budget: raise HTTPException(404, "Orçamento não encontrado.")
    _validate_budget_payload(payload, db)
    data = payload.model_dump()
    items = data.pop("items")
    for key, value in data.items(): setattr(budget, key, value)
    budget.items.clear()
    budget.items.extend(BudgetItem(**item) for item in items)
    try:
        db.commit(); db.refresh(budget)
    except IntegrityError:
        db.rollback(); raise HTTPException(409, "Já existe outro orçamento para esse mês.")
    return db.scalar(_budget_query().where(Budget.id == budget.id))

@router.delete("/budgets/{budget_id}", status_code=204)
def budgets_delete(budget_id: int, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if not budget: raise HTTPException(404, "Orçamento não encontrado.")
    db.delete(budget); db.commit()

@router.get("/budgets/{budget_id}/summary")
def budgets_summary(budget_id: int, db: Session = Depends(get_db)):
    budget = db.scalar(_budget_query().where(Budget.id == budget_id))
    if not budget: raise HTTPException(404, "Orçamento não encontrado.")
    start = budget.reference_month
    end = date(start.year, start.month, monthrange(start.year, start.month)[1])
    rows = []
    total_planned = Decimal("0.00")
    total_realized = Decimal("0.00")
    for item in budget.items:
        category = db.get(Category, item.category_id)
        realized = db.scalar(
            select(func.coalesce(func.sum(FinancialEntry.amount), 0))
            .join(Subgroup, FinancialEntry.subgroup_id == Subgroup.id)
            .join(Group, Subgroup.group_id == Group.id)
            .where(Group.category_id == item.category_id,
                   FinancialEntry.status == "REALIZADO",
                   FinancialEntry.entry_type.in_(["DESPESA", "INVESTIMENTO"]),
                   FinancialEntry.competence_date >= start,
                   FinancialEntry.competence_date <= end)
        ) or Decimal("0.00")
        card_realized = db.scalar(select(func.coalesce(func.sum(CardInstallment.amount), 0)).join(CardPurchase, CardInstallment.purchase_id == CardPurchase.id).join(CreditCard, CardPurchase.card_id == CreditCard.id).join(Subgroup, CardPurchase.subgroup_id == Subgroup.id).join(Group, Subgroup.group_id == Group.id).where(Group.category_id == item.category_id, CardInstallment.invoice_month == start)) or Decimal("0.00")
        realized += card_realized
        planned = item.planned_amount
        total_planned += planned
        total_realized += realized
        rows.append({"category_id": item.category_id, "category_name": category.name,
                     "planned_amount": planned, "planned_percentage": item.planned_percentage,
                     "realized_amount": realized, "remaining_amount": planned - realized,
                     "consumption_percentage": (realized / planned * 100) if planned > 0 else None,
                     "over_budget": realized > planned})
    return {"budget_id": budget.id, "reference_month": start,
            "reference_income": budget.reference_income,
            "total_planned": total_planned, "total_realized": total_realized,
            "total_remaining": total_planned - total_realized,
            "items": rows}

# Indicadores consolidados para o painel inicial.
from datetime import date, timedelta
from calendar import monthrange
from app.models import Group, Subgroup

@router.get("/dashboard/summary")
def dashboard_summary(reference_month: date | None = None, db: Session = Depends(get_db)):
    ref = reference_month or date.today().replace(day=1)
    start = ref.replace(day=1)
    end = ref.replace(day=monthrange(ref.year, ref.month)[1])
    totals = {"RECEITA": Decimal("0.00"), "DESPESA": Decimal("0.00"), "INVESTIMENTO": Decimal("0.00")}
    for kind, amount in db.execute(select(FinancialEntry.entry_type, func.coalesce(func.sum(FinancialEntry.amount), 0)).where(
        FinancialEntry.competence_date >= start, FinancialEntry.competence_date <= end,
        FinancialEntry.status == "REALIZADO").group_by(FinancialEntry.entry_type)).all():
        totals[kind] = Decimal(str(amount))

    card_expenses = db.scalar(select(func.coalesce(func.sum(CardInstallment.amount), 0)).where(CardInstallment.invoice_month == start)) or Decimal("0.00")
    totals["DESPESA"] += card_expenses

    category_rows = db.execute(
        select(Category.id, Category.name, func.coalesce(func.sum(FinancialEntry.amount), 0))
        .join(Group, Group.category_id == Category.id)
        .join(Subgroup, Subgroup.group_id == Group.id)
        .join(FinancialEntry, FinancialEntry.subgroup_id == Subgroup.id)
        .where(FinancialEntry.competence_date >= start, FinancialEntry.competence_date <= end,
               FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type == "DESPESA")
        .group_by(Category.id, Category.name)
    ).all()

    card_category_rows = db.execute(
        select(Category.id, Category.name, func.coalesce(func.sum(CardInstallment.amount), 0))
        .join(Group, Group.category_id == Category.id)
        .join(Subgroup, Subgroup.group_id == Group.id)
        .join(CardPurchase, CardPurchase.subgroup_id == Subgroup.id)
        .join(CardInstallment, CardInstallment.purchase_id == CardPurchase.id)
        .where(CardInstallment.invoice_month == start)
        .group_by(Category.id, Category.name)
    ).all()
    category_totals = {r[0]: [r[1], Decimal(str(r[2]))] for r in category_rows}
    for row in card_category_rows:
        if row[0] in category_totals: category_totals[row[0]][1] += Decimal(str(row[2]))
        else: category_totals[row[0]] = [row[1], Decimal(str(row[2]))]
    category_rows = sorted([(key, value[0], value[1]) for key, value in category_totals.items()], key=lambda r: r[2], reverse=True)[:6]

    recent = db.scalars(select(FinancialEntry).order_by(FinancialEntry.movement_date.desc(), FinancialEntry.id.desc()).limit(8)).all()
    recent_items = [{"id": e.id, "date": e.movement_date.isoformat(), "description": e.description,
                     "entry_type": e.entry_type, "status": e.status, "amount": str(e.amount)} for e in recent]

    flow = []
    cursor = start
    for _ in range(6):
        month_start = cursor.replace(day=1)
        month_end = month_start.replace(day=monthrange(month_start.year, month_start.month)[1])
        vals = {"RECEITA": Decimal("0.00"), "DESPESA": Decimal("0.00")}
        for kind, amount in db.execute(select(FinancialEntry.entry_type, func.coalesce(func.sum(FinancialEntry.amount), 0)).where(
            FinancialEntry.competence_date >= month_start, FinancialEntry.competence_date <= month_end,
            FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type.in_(["RECEITA", "DESPESA"])
        ).group_by(FinancialEntry.entry_type)).all(): vals[kind] = Decimal(str(amount))
        card_month = db.scalar(select(func.coalesce(func.sum(CardInstallment.amount), 0)).where(CardInstallment.invoice_month == month_start)) or Decimal("0.00")
        vals["DESPESA"] += card_month
        flow.append({"month": month_start.isoformat(), "income": str(vals["RECEITA"]), "expenses": str(vals["DESPESA"])})
        previous = month_start - timedelta(days=1)
        cursor = previous.replace(day=1)
    flow.reverse()

    budget = db.scalar(select(Budget).where(Budget.reference_month == start))
    budget_total = None
    if budget:
        from app.models import BudgetItem
        budget_total = str(db.scalar(select(func.coalesce(func.sum(BudgetItem.planned_amount), 0)).where(BudgetItem.budget_id == budget.id)))

    return {"reference_month": start.isoformat(), "income": str(totals["RECEITA"]),
            "expenses": str(totals["DESPESA"]), "investments": str(totals["INVESTIMENTO"]),
            "net_result": str(totals["RECEITA"] - totals["DESPESA"] - totals["INVESTIMENTO"]),
            "expense_categories": [{"category_id": r[0], "category_name": r[1], "amount": str(r[2])} for r in category_rows],
            "recent_entries": recent_items, "monthly_flow": flow, "budget_planned": budget_total}

# Cartões de crédito: compras parceladas compõem despesas por competência da fatura.
from calendar import monthrange as _monthrange
from app.models import CreditCard, CardPurchase, CardInstallment, CardPayment
from app.schemas.core import CreditCardIn, CreditCardOut, CardPurchaseIn, CardPurchaseOut, CardPaymentIn, CardPaymentOut

def _month_add(value: date, offset: int) -> date:
    index = value.year * 12 + value.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)

def _invoice_month(purchase_date: date, closing_day: int) -> date:
    return _month_add(purchase_date.replace(day=1), 0 if purchase_date.day <= closing_day else 1)

def _card_outstanding(card_id: int, db: Session, exclude_purchase_id: int | None = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(CardInstallment.amount), 0)).join(CardPurchase, CardInstallment.purchase_id == CardPurchase.id).where(CardPurchase.card_id == card_id)
    if exclude_purchase_id is not None:
        stmt = stmt.where(CardPurchase.id != exclude_purchase_id)
    total = db.scalar(stmt) or Decimal("0.00")
    payments = db.scalar(select(func.coalesce(func.sum(CardPayment.amount), 0)).where(CardPayment.card_id == card_id)) or Decimal("0.00")
    return max(Decimal("0.00"), total - payments)

def _make_installments(purchase: CardPurchase, card: CreditCard, db: Session):
    total_cents = int(purchase.total_amount * 100)
    base_cents, remainder = divmod(total_cents, purchase.installments_count)
    amounts = [Decimal(base_cents + int(idx < remainder)) / 100 for idx in range(purchase.installments_count)]
    first_month = _invoice_month(purchase.purchase_date, card.closing_day)
    for idx, amount in enumerate(amounts, 1):
        db.add(CardInstallment(purchase_id=purchase.id, installment_number=idx, invoice_month=_month_add(first_month, idx-1), amount=amount))

def _validate_purchase_category(subgroup_id: int | None, db: Session):
    if subgroup_id is None:
        return
    subgroup = db.get(Subgroup, subgroup_id)
    if not subgroup:
        raise HTTPException(404, "Subgrupo não encontrado.")
    group = db.get(Group, subgroup.group_id)
    category = db.get(Category, group.category_id)
    if category.nature not in ("MISTA", "DESPESA"):
        raise HTTPException(422, "A categoria do cartão deve aceitar despesas.")

def _ensure_purchase_editable(purchase: CardPurchase, db: Session):
    months = list(db.scalars(select(CardInstallment.invoice_month).where(CardInstallment.purchase_id == purchase.id)).all())
    if months:
        paid = db.scalar(select(func.count(CardPayment.id)).where(CardPayment.card_id == purchase.card_id, CardPayment.invoice_month.in_(months))) or 0
        if paid:
            raise HTTPException(409, "Não é possível editar ou excluir esta compra: existe pagamento registrado em uma de suas faturas. Ajuste os pagamentos primeiro.")

@router.get("/credit-cards/summary")
def credit_cards_summary(db: Session = Depends(get_db)):
    result = []
    for card in db.scalars(select(CreditCard).order_by(CreditCard.name)).all():
        used = _card_outstanding(card.id, db)
        available = card.credit_limit - used
        result.append({"card_id": card.id, "name": card.name, "credit_limit": str(card.credit_limit), "used": str(used), "available": str(available), "usage_percentage": round(float(used / card.credit_limit * 100), 2)})
    return result

@router.get("/credit-cards", response_model=list[CreditCardOut])
def credit_cards_list(db: Session = Depends(get_db)):
    return list(db.scalars(select(CreditCard).order_by(CreditCard.name)).all())

@router.post("/credit-cards", response_model=CreditCardOut, status_code=201)
def credit_cards_create(payload: CreditCardIn, db: Session = Depends(get_db)):
    return create_item(db, CreditCard, payload)

@router.put("/credit-cards/{card_id}", response_model=CreditCardOut)
def credit_cards_update(card_id: int, payload: CreditCardIn, db: Session = Depends(get_db)):
    card = db.get(CreditCard, card_id)
    if not card: raise HTTPException(404, "Cartão não encontrado.")
    if _card_outstanding(card.id, db) > payload.credit_limit:
        raise HTTPException(422, "O limite informado é menor que o valor atualmente utilizado no cartão.")
    for key, value in payload.model_dump().items(): setattr(card, key, value)
    db.commit(); db.refresh(card); return card

@router.get("/card-purchases", response_model=list[CardPurchaseOut])
def card_purchases_list(db: Session = Depends(get_db)):
    return list(db.scalars(select(CardPurchase).order_by(CardPurchase.purchase_date.desc(), CardPurchase.id.desc())).all())

@router.get("/credit-cards/{card_id}/purchases", response_model=list[CardPurchaseOut])
def credit_card_purchases(card_id: int, db: Session = Depends(get_db)):
    if not db.get(CreditCard, card_id): raise HTTPException(404, "Cartão não encontrado.")
    return list(db.scalars(select(CardPurchase).where(CardPurchase.card_id == card_id).order_by(CardPurchase.purchase_date.desc())).all())

@router.post("/card-purchases", response_model=CardPurchaseOut, status_code=201)
def card_purchase_create(payload: CardPurchaseIn, db: Session = Depends(get_db)):
    card = db.get(CreditCard, payload.card_id)
    if not card: raise HTTPException(404, "Cartão não encontrado.")
    _validate_purchase_category(payload.subgroup_id, db)
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    if int(payload.total_amount * 100) < payload.installments_count:
        raise HTTPException(422, "O valor total deve cobrir pelo menos R$ 0,01 por parcela.")
    if _card_outstanding(card.id, db) + payload.total_amount > card.credit_limit:
        raise HTTPException(422, "A compra ultrapassa o limite disponível do cartão.")
    purchase = CardPurchase(**payload.model_dump())
    db.add(purchase); db.flush()
    _make_installments(purchase, card, db)
    db.commit(); db.refresh(purchase); return purchase

@router.put("/card-purchases/{purchase_id}", response_model=CardPurchaseOut)
def card_purchase_update(purchase_id: int, payload: CardPurchaseIn, db: Session = Depends(get_db)):
    purchase = db.get(CardPurchase, purchase_id)
    if not purchase: raise HTTPException(404, "Compra não encontrada.")
    _ensure_purchase_editable(purchase, db)
    card = db.get(CreditCard, payload.card_id)
    if not card: raise HTTPException(404, "Cartão não encontrado.")
    _validate_purchase_category(payload.subgroup_id, db)
    if payload.person_id is not None and not db.get(Person, payload.person_id): raise HTTPException(404, "Pessoa não encontrada.")
    if int(payload.total_amount * 100) < payload.installments_count:
        raise HTTPException(422, "O valor total deve cobrir pelo menos R$ 0,01 por parcela.")
    if _card_outstanding(card.id, db, exclude_purchase_id=purchase.id) + payload.total_amount > card.credit_limit:
        raise HTTPException(422, "A compra ultrapassa o limite disponível do cartão.")
    new_first_month = _invoice_month(payload.purchase_date, card.closing_day)
    new_months = [_month_add(new_first_month, offset) for offset in range(payload.installments_count)]
    paid_new_months = db.scalar(select(func.count(CardPayment.id)).where(CardPayment.card_id == card.id, CardPayment.invoice_month.in_(new_months))) or 0
    if paid_new_months:
        raise HTTPException(409, "Não é possível mover a compra para uma fatura que já possui pagamento registrado.")
    for key, value in payload.model_dump().items(): setattr(purchase, key, value)
    db.query(CardInstallment).filter(CardInstallment.purchase_id == purchase.id).delete(synchronize_session=False)
    db.flush(); _make_installments(purchase, card, db)
    db.commit(); db.refresh(purchase); return purchase

@router.delete("/card-purchases/{purchase_id}", status_code=204)
def card_purchase_delete(purchase_id: int, db: Session = Depends(get_db)):
    purchase = db.get(CardPurchase, purchase_id)
    if not purchase: raise HTTPException(404, "Compra não encontrada.")
    _ensure_purchase_editable(purchase, db)
    db.delete(purchase); db.commit()

@router.get("/invoices")
def invoices_list(card_id: int | None = None, reference_month: date | None = None, db: Session = Depends(get_db)):
    stmt = select(CardInstallment, CardPurchase, CreditCard).join(CardPurchase, CardInstallment.purchase_id == CardPurchase.id).join(CreditCard, CardPurchase.card_id == CreditCard.id)
    if card_id: stmt = stmt.where(CreditCard.id == card_id)
    if reference_month: stmt = stmt.where(CardInstallment.invoice_month == reference_month.replace(day=1))
    rows = db.execute(stmt.order_by(CardInstallment.invoice_month.desc(), CreditCard.name, CardPurchase.description)).all()
    grouped = {}
    for installment, purchase, card in rows:
        key = (card.id, installment.invoice_month)
        if key not in grouped: grouped[key] = {"card_id": card.id, "card_name": card.name, "invoice_month": installment.invoice_month.isoformat(), "due_date": date(installment.invoice_month.year + (1 if installment.invoice_month.month == 12 else 0), 1 if installment.invoice_month.month == 12 else installment.invoice_month.month + 1, min(card.due_day, _monthrange(installment.invoice_month.year + (1 if installment.invoice_month.month == 12 else 0), 1 if installment.invoice_month.month == 12 else installment.invoice_month.month + 1)[1])).isoformat(), "total": Decimal("0.00"), "paid": Decimal("0.00"), "items": []}
        grouped[key]["total"] += installment.amount
        grouped[key]["items"].append({"description": purchase.description, "installment": f"{installment.installment_number}/{purchase.installments_count}", "amount": str(installment.amount)})
    for item in grouped.values():
        paid = db.scalar(select(func.coalesce(func.sum(CardPayment.amount), 0)).where(CardPayment.card_id == item["card_id"], CardPayment.invoice_month == date.fromisoformat(item["invoice_month"]))) or 0
        item["paid"] = str(paid); item["total"] = str(item["total"]); item["remaining"] = str(max(Decimal("0"), Decimal(item["total"]) - Decimal(str(paid))))
    return list(grouped.values())

@router.post("/card-payments", response_model=CardPaymentOut, status_code=201)
def card_payment_create(payload: CardPaymentIn, db: Session = Depends(get_db)):
    _validate_card_payment(payload, db)
    payment = CardPayment(**payload.model_dump()); db.add(payment); db.commit(); db.refresh(payment); return payment

@router.get("/card-payments", response_model=list[CardPaymentOut])
def card_payments_list(db: Session = Depends(get_db)):
    return list(db.scalars(select(CardPayment).order_by(CardPayment.payment_date.desc(), CardPayment.id.desc())).all())

def _validate_card_payment(payload: CardPaymentIn, db: Session, exclude_payment_id: int | None = None):
    if not db.get(CreditCard, payload.card_id): raise HTTPException(404, "Cartão não encontrado.")
    if not db.get(FinancialAccount, payload.account_id): raise HTTPException(404, "Conta financeira não encontrada.")
    if payload.invoice_month.day != 1: raise HTTPException(422, "A competência da fatura deve ser o primeiro dia do mês.")
    invoice_total = db.scalar(select(func.coalesce(func.sum(CardInstallment.amount), 0)).join(CardPurchase, CardInstallment.purchase_id == CardPurchase.id).where(CardPurchase.card_id == payload.card_id, CardInstallment.invoice_month == payload.invoice_month)) or Decimal("0.00")
    stmt = select(func.coalesce(func.sum(CardPayment.amount), 0)).where(CardPayment.card_id == payload.card_id, CardPayment.invoice_month == payload.invoice_month)
    if exclude_payment_id is not None: stmt = stmt.where(CardPayment.id != exclude_payment_id)
    already_paid = db.scalar(stmt) or Decimal("0.00")
    if invoice_total <= 0: raise HTTPException(404, "Não há compras para a fatura informada.")
    if payload.amount > invoice_total - already_paid: raise HTTPException(422, "O pagamento excede o saldo em aberto da fatura.")

@router.put("/card-payments/{payment_id}", response_model=CardPaymentOut)
def card_payment_update(payment_id: int, payload: CardPaymentIn, db: Session = Depends(get_db)):
    payment = db.get(CardPayment, payment_id)
    if not payment: raise HTTPException(404, "Pagamento não encontrado.")
    _validate_card_payment(payload, db, exclude_payment_id=payment.id)
    for key, value in payload.model_dump().items(): setattr(payment, key, value)
    db.commit(); db.refresh(payment); return payment

@router.delete("/card-payments/{payment_id}", status_code=204)
def card_payment_delete(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(CardPayment, payment_id)
    if not payment: raise HTTPException(404, "Pagamento não encontrado.")
    db.delete(payment); db.commit()
