import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor, require_reviewer
from app.database import get_db
from app.events import log_action, notify
from app.models import Invoice, Payment, Vendor
from app.pdf import build_payment_advice_pdf
from app.schemas import PaymentInitiate, PaymentOut, PaymentStatusUpdate

router = APIRouter(prefix="/payments", tags=["payments"])

# Per FR-VEP-009: a payment may only move forward through these stages.
# Repeated/duplicate bank callbacks that don't advance the stage are
# accepted idempotently rather than creating a new state transition.
VALID_TRANSITIONS = {
    "Initiated": {"Processing", "Failed"},
    "Processing": {"Credited", "Failed", "Returned"},
    "Credited": {"Reversed"},
    "Failed": set(),
    "Returned": set(),
    "Reversed": set(),
}

# Per FR-VEP-008: an expected/service-level timeline for the current
# stage. Simple fixed day-counts, same convention as the SLA due_dates
# used elsewhere in this project (e.g. pension_mgmt's bank requests).
STAGE_SLA_DAYS = {"Initiated": 2, "Processing": 3}


def _to_out(payment: Payment, invoice: Invoice) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    out.invoice_number = invoice.invoice_number
    sla_days = STAGE_SLA_DAYS.get(payment.status)
    out.expected_completion_date = (payment.server_date.date() + timedelta(days=sla_days)) if sla_days else None
    return out


@router.get("", response_model=list[PaymentOut])
def list_payments(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, description="Matches invoice number or payment reference"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
):
    """A reviewer sees every payment; a vendor sees only payments against
    their own invoices. Supports the search/filter requirements of
    FR-VEP-008 (invoice number, payment reference, date range, status,
    amount range)."""
    query = db.query(Payment, Invoice).join(Invoice, Payment.invoice_id == Invoice.id).filter(Payment.is_deleted.is_(False))
    if vendor.role != "reviewer":
        query = query.filter(Invoice.vendor_id == vendor.id)
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.filter((Invoice.invoice_number.ilike(like)) | (Payment.payment_reference.ilike(like)))
    if date_from:
        query = query.filter(Payment.server_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Payment.server_date <= datetime.combine(date_to, datetime.max.time()))
    if min_amount is not None:
        query = query.filter(Payment.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Payment.amount <= max_amount)

    rows = query.order_by(Payment.server_date.desc()).all()
    return [_to_out(payment, invoice) for payment, invoice in rows]


@router.post("/invoices/{invoice_id}/initiate", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def initiate_payment(invoice_id: int, payload: PaymentInitiate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted.is_(False)).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status != "Approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only an approved invoice can be paid")

    payment = Payment(
        invoice_id=invoice.id, payment_reference=f"PAY-{datetime.utcnow().year}-{random.randint(100000, 999999)}",
        amount=invoice.total_amount, mode_of_payment=payload.mode_of_payment, processed_by=reviewer.id,
    )
    invoice.status = "Payment Initiated"
    db.add(payment)
    db.commit()
    db.refresh(payment)

    log_action(db, vendor_id=invoice.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action="Payment initiated", entity_type="Payment", entity_id=payment.id)
    notify(
        db, vendor_id=invoice.vendor_id, title="Payment initiated",
        message=f"Payment {payment.payment_reference} of {payment.amount} has been initiated for invoice {invoice.invoice_number}.", category="Payment",
    )
    db.commit()
    return _to_out(payment, invoice)


@router.post("/{payment_id}/status", response_model=PaymentOut)
def update_payment_status(payment_id: int, payload: PaymentStatusUpdate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """Stands in for a real banking-network status callback -- the
    reviewer manually advances the payment the way the bank's system
    would in production. Repeated callbacks for a stage already reached
    are accepted without creating a duplicate transition (idempotency,
    per FR-VEP-009)."""
    if payload.status not in ("Processing", "Credited", "Failed", "Returned", "Reversed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    payment = db.query(Payment).filter(Payment.id == payment_id, Payment.is_deleted.is_(False)).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()

    if payment.status == payload.status:
        payment.reconciliation_status = "Matched"
        db.commit()
        db.refresh(payment)
        return _to_out(payment, invoice)  # idempotent no-op: same callback received twice

    if payload.status not in VALID_TRANSITIONS.get(payment.status, set()):
        payment.reconciliation_status = "Exception"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move payment from {payment.status} to {payload.status}; placed in exception queue for review",
        )

    payment.status = payload.status
    payment.bank_reference = payload.bank_reference or payment.bank_reference
    payment.response_code = payload.response_code
    payment.response_message = payload.response_message
    payment.callback_timestamp = datetime.utcnow()
    payment.reconciliation_status = "Matched"
    payment.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)

    if payload.status == "Credited":
        invoice.status = "Paid / Credited"
    elif payload.status in ("Failed", "Returned", "Reversed"):
        invoice.status = f"Payment {payload.status}"
    else:
        invoice.status = "Processing"

    log_action(db, vendor_id=invoice.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action=f"Payment {payload.status.lower()}", entity_type="Payment", entity_id=payment.id, after_value=payload.status)
    notify(
        db, vendor_id=invoice.vendor_id, title=f"Payment {payload.status.lower()}",
        message=f"Payment {payment.payment_reference} is now {payload.status.lower()}.", category="Payment",
    )
    db.commit()
    return _to_out(payment, invoice)


@router.get("/{payment_id}/advice")
def download_payment_advice(payment_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    invoice = db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
    if vendor.role != "reviewer" and invoice.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this payment advice")

    target_vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    pdf_bytes = build_payment_advice_pdf(payment, invoice, target_vendor, language=vendor.preferred_language)
    log_action(db, vendor_id=invoice.vendor_id, actor_id=vendor.id, actor_role=vendor.role, action="Payment advice downloaded", entity_type="Payment", entity_id=payment.id)
    db.commit()
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payment_advice_{payment.payment_reference}.pdf"},
    )
