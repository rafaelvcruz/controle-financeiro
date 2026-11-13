from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401 - registra todos os modelos

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
