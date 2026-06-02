from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.constants import MEDIA_PATH
from app.dependencies.auth import get_current_user
from app.routers import (
    api_keys,
    audit_log,
    auth,
    bank_statements,
    documents,
    receipts,
    reconciliation,
    references,
    transactions,
)

app = FastAPI(title="buh-manager", version="1.0.0")

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.is_local:
    app.mount("/media", StaticFiles(directory=MEDIA_PATH), name="media")

_protected: dict[str, Any] = {"dependencies": [Depends(get_current_user)]}

app.include_router(auth.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1", **_protected)
app.include_router(documents.router, prefix="/api/v1", **_protected)
app.include_router(receipts.router, prefix="/api/v1", **_protected)
app.include_router(bank_statements.router, prefix="/api/v1", **_protected)
app.include_router(transactions.router, prefix="/api/v1", **_protected)
app.include_router(reconciliation.router, prefix="/api/v1", **_protected)
app.include_router(references.router, prefix="/api/v1", **_protected)
app.include_router(audit_log.router, prefix="/api/v1", **_protected)
