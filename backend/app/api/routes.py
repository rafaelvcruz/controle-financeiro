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
