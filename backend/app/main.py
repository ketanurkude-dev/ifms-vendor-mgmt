from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import approver, audit, auth, contracts, invoices, notifications, payments, reports, vendor
from app.seed import seed_demo_accounts

# Creates tables on startup if they don't exist yet (simple approach, no migrations tool).
Base.metadata.create_all(bind=engine)


def _seed() -> None:
    db = SessionLocal()
    try:
        seed_demo_accounts(db)
    finally:
        db.close()


_seed()

app = FastAPI(title="Vendor Portal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vendor.router)
app.include_router(approver.router)
app.include_router(contracts.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(notifications.router)
app.include_router(audit.router)
app.include_router(reports.router)


@app.get("/")
def root():
    return {"status": "ok"}
