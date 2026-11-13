from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class PersonIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    active: bool = True
class PersonOut(PersonIn, ORMModel):
    id: int

class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    nature: str = "MISTA"
    suggested_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    active: bool = True
class CategoryOut(CategoryIn, ORMModel):
    id: int

class GroupIn(BaseModel):
    category_id: int
    name: str = Field(min_length=2, max_length=80)
    active: bool = True
class GroupOut(GroupIn, ORMModel):
    id: int

class SubgroupIn(BaseModel):
    group_id: int
    name: str = Field(min_length=2, max_length=100)
    active: bool = True
class SubgroupOut(SubgroupIn, ORMModel):
    id: int

class AccountIn(BaseModel):
    person_id: int | None = None
    name: str = Field(min_length=2, max_length=100)
    account_type: str = Field(min_length=2, max_length=30)
    initial_balance: Decimal = Decimal("0.00")
    balance_date: date
    active: bool = True
    notes: str | None = None
class AccountOut(AccountIn, ORMModel):
    id: int
