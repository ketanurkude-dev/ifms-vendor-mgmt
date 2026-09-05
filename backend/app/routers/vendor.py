from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor
from app.credential_verification import run_credential_verification
from app.database import get_db
from app.events import log_action, notify
from app.models import (
    CRITICAL_PROFILE_FIELDS,
    MANDATORY_DOC_TYPES,
    Contract,
    Invoice,
    Payment,
    ProfileChangeRequest,
    Vendor,
    VendorApplicationEvent,
    VendorDocument,
)
from app.schemas import (
    LanguageUpdate,
    OtpRequest,
    PendingAction,
    ProfileChangeCreate,
    ProfileChangeOut,
    ProfileUpdate,
    VendorDashboardOut,
    VendorDocumentOut,
    VendorOut,
)
from app.storage import guess_media_type, read_stored_file, save_upload, validate_upload

router = APIRouter(prefix="/vendor", tags=["vendor"])


@router.get("/me", response_model=VendorOut)
def get_my_profile(vendor: Vendor = Depends(get_current_vendor)):
    return vendor


@router.put("/language", response_model=VendorOut)
def set_language(payload: LanguageUpdate, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if payload.language not in ("en", "hi"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Language must be 'en' or 'hi'")
    vendor.preferred_language = payload.language
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/dashboard", response_model=VendorDashboardOut)
def get_dashboard(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    documents = db.query(VendorDocument).filter(VendorDocument.vendor_id == vendor.id, VendorDocument.is_deleted.is_(False)).all()

    # Profile completeness: how many of the "should be filled" fields are non-empty.
    fields = [
        vendor.legal_name, vendor.contact_person_name, vendor.email, vendor.mobile, vendor.address,
        vendor.pan_number, vendor.gstin_number, vendor.bank_account_number, vendor.bank_ifsc, vendor.bank_name,
    ]
    filled = sum(1 for f in fields if f)
    completeness = round(filled / len(fields) * 100)
    if vendor.email_verified:
        completeness = min(100, completeness + 5)
    if vendor.mobile_verified:
        completeness = min(100, completeness + 5)

    pending: list[PendingAction] = []
    if vendor.status in ("Draft", "Returned"):
        if not vendor.email_verified:
            pending.append(PendingAction(kind="otp", message="Verify your registered email address"))
        if not vendor.mobile_verified:
            pending.append(PendingAction(kind="otp", message="Verify your registered mobile number"))
        missing_docs = set(MANDATORY_DOC_TYPES.get(vendor.vendor_type, [])) - {d.doc_type for d in documents}
        for doc_type in missing_docs:
            pending.append(PendingAction(kind="document", message=f"Upload mandatory document: {doc_type}"))
    if vendor.status == "Returned":
        pending.append(PendingAction(kind="clarification", message=f"Application returned: {vendor.review_remarks or 'see remarks'}"))

    expiring_docs = [d for d in documents if d.expiry_date and (d.expiry_date - datetime.utcnow().date()).days <= 30]
    for doc in expiring_docs:
        pending.append(PendingAction(kind="expiry", message=f"{doc.doc_type} is expiring on {doc.expiry_date}"))

    rejected_invoices = (
        db.query(Invoice).filter(Invoice.vendor_id == vendor.id, Invoice.status == "Rejected", Invoice.is_deleted.is_(False)).all()
    )
    for inv in rejected_invoices:
        pending.append(PendingAction(kind="invoice", message=f"Invoice {inv.invoice_number} was rejected"))

    open_changes = (
        db.query(ProfileChangeRequest)
        .filter(ProfileChangeRequest.vendor_id == vendor.id, ProfileChangeRequest.status == "Submitted")
        .count()
    )
    if open_changes:
        pending.append(PendingAction(kind="profile", message=f"{open_changes} profile change request(s) awaiting review"))

    invoice_summary: dict[str, int] = {}
    for inv in db.query(Invoice).filter(Invoice.vendor_id == vendor.id, Invoice.is_deleted.is_(False)).all():
        invoice_summary[inv.status] = invoice_summary.get(inv.status, 0) + 1

    payments = (
        db.query(Payment)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.vendor_id == vendor.id, Payment.is_deleted.is_(False))
        .all()
    )
    total_paid = sum(float(p.amount) for p in payments if p.status == "Credited")
    pending_amount = sum(float(p.amount) for p in payments if p.status in ("Initiated", "Processing"))
    payment_summary = {
        "payment_count": len(payments),
        "total_credited": total_paid,
        "pending_amount": pending_amount,
        "recent_status": payments[-1].status if payments else "-",
    }

    contract_count = db.query(Contract).filter(Contract.vendor_id == vendor.id, Contract.is_deleted.is_(False)).count()

    return VendorDashboardOut(
        vendor=vendor,
        profile_completeness_percent=completeness,
        pending_actions=pending,
        invoice_summary=invoice_summary,
        payment_summary=payment_summary,
        contract_count=contract_count,
    )


@router.put("/profile", response_model=VendorOut)
def update_profile(payload: ProfileUpdate, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """Only non-critical fields update immediately. Legal name, PAN,
    GSTIN, bank details, email, and mobile go through /profile-changes
    instead, since those require re-approval per FR-VEP-004."""
    before = f"trade_name={vendor.trade_name}, contact={vendor.contact_person_name}, address={vendor.address}, bank_name={vendor.bank_name}"
    if payload.trade_name is not None:
        vendor.trade_name = payload.trade_name
        vendor.company_name = payload.trade_name or vendor.legal_name
    if payload.contact_person_name is not None:
        vendor.contact_person_name = payload.contact_person_name
    if payload.address is not None:
        vendor.address = payload.address
    if payload.bank_name is not None:
        vendor.bank_name = payload.bank_name
    vendor.profile_version += 1
    db.commit()
    db.refresh(vendor)

    after = f"trade_name={vendor.trade_name}, contact={vendor.contact_person_name}, address={vendor.address}, bank_name={vendor.bank_name}"
    log_action(
        db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Profile updated",
        entity_type="Vendor", entity_id=vendor.id, before_value=before, after_value=after,
    )
    db.commit()
    return vendor


@router.get("/profile-changes", response_model=list[ProfileChangeOut])
def list_profile_changes(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    return (
        db.query(ProfileChangeRequest)
        .filter(ProfileChangeRequest.vendor_id == vendor.id)
        .order_by(ProfileChangeRequest.server_date.desc())
        .all()
    )


@router.post("/profile-changes", response_model=ProfileChangeOut, status_code=status.HTTP_201_CREATED)
def request_profile_change(payload: ProfileChangeCreate, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if payload.field_name not in CRITICAL_PROFILE_FIELDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"field_name must be one of {CRITICAL_PROFILE_FIELDS}")

    old_value = str(getattr(vendor, payload.field_name))
    change = ProfileChangeRequest(
        vendor_id=vendor.id, field_name=payload.field_name, old_value=old_value, new_value=payload.new_value, reason=payload.reason
    )
    db.add(change)
    log_action(
        db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Profile change requested",
        entity_type="ProfileChangeRequest", entity_id=None, before_value=old_value, after_value=payload.new_value,
    )
    db.commit()
    db.refresh(change)
    return change


# The email/mobile OTPs below are mocked exactly like the login OTP: any
# 6-digit value is accepted. There is no real SMS/email gateway in this
# prototype -- see app/routers/auth.py for the same convention.


@router.post("/send-email-otp")
def send_email_otp(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="OTP sent (email)", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    return {"message": f"A 6-digit OTP has been sent to {vendor.email} (demo: enter any 6 digits)."}


@router.post("/verify-email-otp", response_model=VendorOut)
def verify_email_otp(payload: OtpRequest, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if not payload.otp.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP must be 6 digits")
    vendor.email_verified = True
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="OTP verified (email)", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.post("/send-mobile-otp")
def send_mobile_otp(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="OTP sent (mobile)", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    return {"message": f"A 6-digit OTP has been sent to {vendor.mobile} (demo: enter any 6 digits)."}


@router.post("/verify-mobile-otp", response_model=VendorOut)
def verify_mobile_otp(payload: OtpRequest, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if not payload.otp.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP must be 6 digits")
    vendor.mobile_verified = True
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="OTP verified (mobile)", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    db.refresh(vendor)
    return vendor


def _doc_out(document: VendorDocument) -> VendorDocumentOut:
    out = VendorDocumentOut.model_validate(document)
    out.has_file = bool(document.stored_path)
    return out


@router.get("/documents", response_model=list[VendorDocumentOut])
def list_my_documents(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    documents = (
        db.query(VendorDocument)
        .filter(VendorDocument.vendor_id == vendor.id, VendorDocument.is_deleted.is_(False))
        .order_by(VendorDocument.server_date)
        .all()
    )
    return [_doc_out(d) for d in documents]


@router.post("/documents", response_model=VendorDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    doc_type: str = Form(...),
    expiry_date: date | None = Form(default=None),
    file: UploadFile = File(...),
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    """The file is written to local disk (app/uploads/) and read back on
    download -- a real, if local-only, stand-in for the IFMS Document
    Management System. A re-upload of the same document type bumps the
    version instead of starting a fresh checklist entry."""
    validate_upload(file)
    contents = await file.read()
    stored_path = save_upload(file, f"vendor_documents/{vendor.id}", contents)

    previous = (
        db.query(VendorDocument)
        .filter(VendorDocument.vendor_id == vendor.id, VendorDocument.doc_type == doc_type, VendorDocument.is_deleted.is_(False))
        .order_by(VendorDocument.version.desc())
        .first()
    )
    next_version = (previous.version + 1) if previous else 1
    if previous:
        previous.is_deleted = True  # superseded by the new version

    document = VendorDocument(
        vendor_id=vendor.id, doc_type=doc_type, file_name=file.filename, stored_path=stored_path,
        version=next_version, expiry_date=expiry_date,
    )
    db.add(document)
    log_action(
        db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Document uploaded",
        entity_type="VendorDocument", entity_id=None, after_value=f"{doc_type} v{next_version}",
    )
    db.commit()
    db.refresh(document)
    return _doc_out(document)


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    document = db.query(VendorDocument).filter(VendorDocument.id == document_id).first()
    if not document or not document.stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if vendor.role != "reviewer" and document.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document")

    contents = read_stored_file(document.stored_path)
    return Response(content=contents, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={document.file_name}"})


@router.get("/documents/{document_id}/view")
def view_document(document_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """Same file as /download, but served inline with the real content
    type so a browser tab can render the PDF/image instead of saving it."""
    document = db.query(VendorDocument).filter(VendorDocument.id == document_id).first()
    if not document or not document.stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if vendor.role != "reviewer" and document.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document")

    contents = read_stored_file(document.stored_path)
    media_type = guess_media_type(document.file_name)
    return Response(content=contents, media_type=media_type, headers={"Content-Disposition": f"inline; filename={document.file_name}"})


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    document = db.query(VendorDocument).filter(VendorDocument.id == document_id, VendorDocument.vendor_id == vendor.id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    document.is_deleted = True
    log_action(
        db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Document deleted",
        entity_type="VendorDocument", entity_id=document.id, before_value=document.doc_type,
    )
    db.commit()
    return {"message": "Document deleted"}


@router.post("/submit-application", response_model=VendorOut)
def submit_application(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if vendor.status not in ("Draft", "Returned"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application has already been submitted")
    if not (vendor.email_verified and vendor.mobile_verified):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verify your email and mobile before submitting")

    documents = (
        db.query(VendorDocument).filter(VendorDocument.vendor_id == vendor.id, VendorDocument.is_deleted.is_(False)).all()
    )
    uploaded_types = {d.doc_type for d in documents}
    missing = set(MANDATORY_DOC_TYPES.get(vendor.vendor_type, [])) - uploaded_types
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing mandatory documents: {', '.join(sorted(missing))}")

    vendor.status = "Submitted"
    vendor.submitted_at = datetime.utcnow()
    db.add(VendorApplicationEvent(vendor_id=vendor.id, action="Submitted", actor_id=vendor.id))
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Submitted application", entity_type="Vendor", entity_id=vendor.id)
    notify(
        db, vendor_id=vendor.id, title="Registration submitted",
        message="Your registration has been submitted and is awaiting review.", category="Registration",
    )
    db.commit()

    # FR-VEP-002: kick off automatic credential verification as soon as
    # the application reaches the reviewer's queue.
    run_credential_verification(db, vendor)
    db.commit()
    db.refresh(vendor)
    return vendor
