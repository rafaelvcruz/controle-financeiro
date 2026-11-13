from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="Controle Financeiro Familiar API", version="0.1.0", description="API local para controle financeiro familiar.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["*"])
app.include_router(router)
