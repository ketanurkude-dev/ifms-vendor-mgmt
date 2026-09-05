from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor, require_reviewer
from app.csv_export import rows_to_csv_response
from app.database import get_db
from app.models import Contract, CredentialVerification, Invoice, Notification, Payment, Vendor, VendorDocument

router = APIRouter(prefix="/reports", tags=["reports"])

# ---------------------------------------------------------------------
# 4.1 Vendor-facing reports (RPT-VEP-001 to RPT-VEP-007)
# ---------------------------------------------------------------------


@router.get("/registration-status")
def registration_status_report(vendor: Vendor = Depends(get_current_vendor)):
    """RPT-VEP-001."""
    return {
        "application_reference": vendor.application_reference,
        "submitted_date": vendor.submitted_at,
        "current_stage": vendor.status,
        "pending_action": vendor.review_remarks if vendor.status == "Returned" else None,
        "reviewer_remarks": vendor.review_remarks,
    }


@router.get("/profile-document-status")
def profile_document_status_report(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """RPT-VEP-002."""
    documents = db.query(VendorDocument).filter(VendorDocument.vendor_id == vendor.id, VendorDocument.is_deleted.is_(False)).all()
    return {
        "profile": {
            "legal_name": vendor.legal_name, "trade_name": vendor.trade_name, "vendor_type": vendor.vendor_type,
            "email": vendor.email, "mobile": vendor.mobile, "status": vendor.status,
        },
        "documents": [
            {
                "doc_type": d.doc_type, "file_name": d.file_name, "verification_status": d.verification_status,
                "expiry_date": d.expiry_date, "expiring_soon": bool(d.expiry_date and (d.expiry_date - date.today()).days <= 30),
            }
            for d in documents
        ],
    }


@router.get("/invoice-register")
def invoice_register_report(
    vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db), format: str | None = None,
    date_from: date | None = Query(default=None), date_to: date | None = Query(default=None),
):
    """RPT-VEP-003."""
    query = db.query(Invoice).filter(Invoice.vendor_id == vendor.id, Invoice.is_deleted.is_(False))
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)
    rows = [
        {
            "invoice_number": i.invoice_number, "invoice_date": i.invoice_date, "contract_id": i.contract_id,
            "amount": float(i.total_amount), "status": i.status, "pending_with": "Reviewer" if i.status == "Submitted" else "-",
            "remarks": i.review_remarks or "",
        }
        for i in query.order_by(Invoice.invoice_date.desc()).all()
    ]
    if format == "csv":
        return rows_to_csv_response(rows, "invoice_register.csv")
    return rows


@router.get("/payment-status")
def payment_status_report(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db), format: str | None = None):
    """RPT-VEP-004."""
    payments = (
        db.query(Payment).join(Invoice).filter(Invoice.vendor_id == vendor.id, Payment.is_deleted.is_(False)).all()
    )
    rows = [
        {
            "invoice_id": p.invoice_id, "payment_reference": p.payment_reference, "amount": float(p.amount),
            "stage": p.status, "payment_date": p.processed_at, "bank_reference": p.bank_reference or "", "status": p.status,
        }
        for p in payments
    ]
    if format == "csv":
        return rows_to_csv_response(rows, "payment_status.csv")
    return rows


@router.get("/contract-summary")
def contract_summary_report(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """RPT-VEP-006."""
    contracts = db.query(Contract).filter(Contract.vendor_id == vendor.id, Contract.is_deleted.is_(False)).all()
    return [
        {
            "contract_number": c.contract_number, "title": c.title, "department": c.department,
            "value": float(c.contract_value), "start_date": c.start_date, "end_date": c.end_date, "status": c.status,
        }
        for c in contracts
    ]


@router.get("/vendor-performance")
def vendor_performance_report(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """RPT-VEP-007."""
    contracts = db.query(Contract).filter(Contract.vendor_id == vendor.id, Contract.is_deleted.is_(False)).all()
    return [
        {
            "contract_number": c.contract_number, "measurement_period": f"{c.start_date} to {c.end_date}",
            "performance_rating": c.performance_rating, "remarks": c.performance_remarks, "source": "Vendor Portal (self-contained)",
        }
        for c in contracts
    ]


# ---------------------------------------------------------------------
# 4.2 Departmental MIS reports (RPT-VEP-101 to RPT-VEP-108)
# ---------------------------------------------------------------------


@router.get("/registration-pipeline")
def registration_pipeline_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-101."""
    counts: dict[str, int] = {}
    for v in db.query(Vendor).filter(Vendor.role == "vendor", Vendor.is_deleted.is_(False)).all():
        counts[v.status] = counts.get(v.status, 0) + 1
    return counts


@router.get("/verification-exceptions")
def verification_exceptions_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-102."""
    exceptions = (
        db.query(CredentialVerification)
        .filter(CredentialVerification.status.in_(["Mismatch", "Failed", "Manual Review Required"]))
        .order_by(CredentialVerification.server_date.desc())
        .all()
    )
    today = date.today()
    expired_docs = db.query(VendorDocument).filter(VendorDocument.expiry_date.isnot(None), VendorDocument.expiry_date < today, VendorDocument.is_deleted.is_(False)).all()
    return {
        "credential_exceptions": [
            {"vendor_id": e.vendor_id, "credential_type": e.credential_type, "status": e.status, "reason": e.mismatch_reason}
            for e in exceptions
        ],
        "expired_documents": [
            {"vendor_id": d.vendor_id, "doc_type": d.doc_type, "expiry_date": d.expiry_date} for d in expired_docs
        ],
    }


@router.get("/invoice-aging")
def invoice_aging_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db), format: str | None = None):
    """RPT-VEP-103."""
    invoices = db.query(Invoice).filter(Invoice.is_deleted.is_(False)).all()
    today = date.today()
    rows = [
        {
            "invoice_number": i.invoice_number, "vendor_id": i.vendor_id, "contract_id": i.contract_id,
            "status": i.status, "value": float(i.total_amount), "age_days": (today - i.invoice_date).days,
        }
        for i in invoices
    ]
    if format == "csv":
        return rows_to_csv_response(rows, "invoice_aging.csv")
    return rows


@router.get("/payment-aging")
def payment_aging_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-104."""
    approved_unpaid = (
        db.query(Invoice).filter(Invoice.status == "Approved", Invoice.is_deleted.is_(False)).all()
    )
    payments = db.query(Payment).filter(Payment.is_deleted.is_(False)).all()
    initiated_not_credited = [p for p in payments if p.status in ("Initiated", "Processing")]
    failed_or_returned = [p for p in payments if p.status in ("Failed", "Returned", "Reversed")]
    overdue_days = 15
    overdue = [
        p for p in initiated_not_credited
        if (datetime.utcnow() - p.server_date).days > overdue_days
    ]
    return {
        "approved_but_unpaid": [{"invoice_number": i.invoice_number, "value": float(i.total_amount)} for i in approved_unpaid],
        "initiated_not_credited": [{"payment_reference": p.payment_reference, "status": p.status} for p in initiated_not_credited],
        "failed_or_returned": [{"payment_reference": p.payment_reference, "status": p.status} for p in failed_or_returned],
        "overdue": [{"payment_reference": p.payment_reference, "days_pending": (datetime.utcnow() - p.server_date).days} for p in overdue],
    }


@router.get("/vendor-payment-summary")
def vendor_payment_summary_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-105."""
    summary: dict[int, dict] = {}
    invoices = db.query(Invoice).filter(Invoice.is_deleted.is_(False)).all()
    for inv in invoices:
        entry = summary.setdefault(inv.vendor_id, {"vendor_id": inv.vendor_id, "invoice_count": 0, "paid_value": 0.0, "pending_value": 0.0, "failed_returned_count": 0})
        entry["invoice_count"] += 1
        if inv.status == "Paid / Credited":
            entry["paid_value"] += float(inv.total_amount)
        elif inv.status in ("Submitted", "Approved", "Payment Initiated", "Processing"):
            entry["pending_value"] += float(inv.total_amount)
        elif inv.status.startswith("Payment "):
            entry["failed_returned_count"] += 1
    return list(summary.values())


@router.get("/contract-performance")
def contract_performance_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-106."""
    contracts = db.query(Contract).filter(Contract.is_deleted.is_(False)).all()
    return [
        {
            "contract_number": c.contract_number, "vendor_id": c.vendor_id, "status": c.status,
            "performance_rating": c.performance_rating, "remarks": c.performance_remarks,
        }
        for c in contracts
    ]


@router.get("/notification-delivery")
def notification_delivery_report(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    """RPT-VEP-107. No real email/SMS gateway is wired up in this
    prototype, so every notification is 'delivered' through the portal
    channel only -- the report shape and delivery-status field are real,
    the channel is limited to what's actually implemented."""
    notifications = db.query(Notification).order_by(Notification.server_date.desc()).limit(500).all()
    return [
        {"vendor_id": n.vendor_id, "event": n.title, "category": n.category, "channel": "Portal", "delivery_status": "Delivered", "read_status": n.is_read}
        for n in notifications
    ]
