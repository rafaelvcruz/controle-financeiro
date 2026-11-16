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
        received = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.to_account_id == account.id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
        result.append({"id": account.id, "name": account.name, "account_type": account.account_type, "person_id": account.person_id, "initial_balance": account.initial_balance, "balance_date": account.balance_date, "active": account.active, "balance": account.initial_balance + income + received - expenses - sent})
    return result

@router.get("/accounts/{account_id}/balance")
def account_balance(account_id: int, db: Session = Depends(get_db)):
    account = db.get(FinancialAccount, account_id)
    if not account: raise HTTPException(404, "Conta financeira não encontrada.")
    income = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account_id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type == "RECEITA", FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
    expenses = db.scalar(select(func.coalesce(func.sum(FinancialEntry.amount), 0)).where(FinancialEntry.account_id == account_id, FinancialEntry.status == "REALIZADO", FinancialEntry.entry_type.in_(["DESPESA", "INVESTIMENTO"]), FinancialEntry.movement_date >= account.balance_date)) or Decimal("0")
    sent = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.from_account_id == account_id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
    received = db.scalar(select(func.coalesce(func.sum(AccountTransfer.amount), 0)).where(AccountTransfer.to_account_id == account_id, AccountTransfer.status == "REALIZADO", AccountTransfer.movement_date >= account.balance_date)) or Decimal("0")
    balance = account.initial_balance + income + received - expenses - sent
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
    db.flush()
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
