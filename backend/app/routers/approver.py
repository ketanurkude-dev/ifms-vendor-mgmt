import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_reviewer
from app.database import get_db
from app.events import log_action, notify
from app.models import CredentialVerification, ProfileChangeRequest, Vendor, VendorApplicationEvent, VendorDocument
from app.schemas import (
    ApplicationDetailOut,
    ApplicationQueueItem,
    DocumentReviewRequest,
    ManualVerificationDecision,
    ProfileChangeOut,
    ReviewRequest,
    VendorDocumentOut,
)

router = APIRouter(prefix="/approver", tags=["approver"])


@router.get("/applications", response_model=list[ApplicationQueueItem])
def get_application_queue(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    vendors = (
        db.query(Vendor)
        .filter(Vendor.status == "Submitted", Vendor.is_deleted.is_(False))
        .order_by(Vendor.submitted_at)
        .all()
    )
    return [
        ApplicationQueueItem(
            id=v.id,
            application_reference=v.application_reference,
            vendor_type=v.vendor_type,
            company_name=v.company_name,
            contact_person_name=v.contact_person_name,
            email=v.email,
            mobile=v.mobile,
            address=v.address,
            pan_number=v.pan_number,
            gstin_number=v.gstin_number,
            status=v.status,
            submitted_at=v.submitted_at,
            server_date=v.server_date,
        )
        for v in vendors
    ]


@router.get("/applications/{vendor_id}", response_model=ApplicationDetailOut)
def get_application_detail(vendor_id: int, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.is_deleted.is_(False)).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")

    documents = (
        db.query(VendorDocument)
        .filter(VendorDocument.vendor_id == vendor_id, VendorDocument.is_deleted.is_(False))
        .order_by(VendorDocument.server_date)
        .all()
    )
    events = (
        db.query(VendorApplicationEvent).filter(VendorApplicationEvent.vendor_id == vendor_id).order_by(VendorApplicationEvent.server_date).all()
    )
    verifications = (
        db.query(CredentialVerification)
        .filter(CredentialVerification.vendor_id == vendor_id)
        .order_by(CredentialVerification.server_date.desc())
        .all()
    )
    documents_out = []
    for d in documents:
        out = VendorDocumentOut.model_validate(d)
        out.has_file = bool(d.stored_path)
        documents_out.append(out)
    return ApplicationDetailOut(vendor=vendor, documents=documents_out, events=events, credential_verifications=verifications)


def _generate_vendor_code() -> str:
    return f"VEN-{datetime.utcnow().year}-{random.randint(10000, 99999)}"


@router.post("/applications/{vendor_id}/review", response_model=None)
def review_application(vendor_id: int, payload: ReviewRequest, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    if payload.status not in ("Approved", "Rejected", "Returned"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.is_deleted.is_(False)).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    if vendor.status != "Submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a submitted application can be reviewed")
    if payload.status in ("Returned", "Rejected") and not payload.review_remarks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Remarks are required to return or reject an application")

    vendor.status = payload.status
    vendor.reviewed_by = reviewer.id
    vendor.review_remarks = payload.review_remarks
    vendor.reviewed_at = datetime.utcnow()
    if payload.status == "Approved" and not vendor.vendor_code:
        vendor.vendor_code = _generate_vendor_code()

    db.add(VendorApplicationEvent(vendor_id=vendor.id, action=payload.status, remarks=payload.review_remarks, actor_id=reviewer.id))
    log_action(
        db, vendor_id=vendor.id, actor_id=reviewer.id, actor_role=reviewer.role, action=f"Application {payload.status.lower()}",
        entity_type="Vendor", entity_id=vendor.id, before_value="Submitted", after_value=payload.status, details=payload.review_remarks,
    )
    notify(
        db, vendor_id=vendor.id, title=f"Registration {payload.status.lower()}",
        message=payload.review_remarks or f"Your registration has been {payload.status.lower()}.", category="Registration",
    )
    db.commit()
    return {"message": f"Application {payload.status.lower()}"}


@router.post("/documents/{document_id}/review", response_model=VendorDocumentOut)
def review_document(document_id: int, payload: DocumentReviewRequest, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    if payload.verification_status not in ("Verified", "Rejected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification status")

    document = db.query(VendorDocument).filter(VendorDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document.verification_status = payload.verification_status
    document.remarks = payload.remarks
    log_action(
        db, vendor_id=document.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action="Document reviewed",
        entity_type="VendorDocument", entity_id=document.id, after_value=payload.verification_status, details=payload.remarks,
    )
    db.commit()
    db.refresh(document)
    out = VendorDocumentOut.model_validate(document)
    out.has_file = bool(document.stored_path)
    return out


@router.post("/credential-verifications/{verification_id}/decision")
def decide_credential_verification(
    verification_id: int, payload: ManualVerificationDecision, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)
):
    """Per FR-VEP-002: a reviewer records the manual decision for a
    credential check that came back Mismatch, Failed, or Manual Review
    Required from the (simulated) automatic verification."""
    if payload.status not in ("Verified", "Mismatch", "Failed", "Not Available", "Manual Review Required"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    record = db.query(CredentialVerification).filter(CredentialVerification.id == verification_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification record not found")

    before = record.status
    record.status = payload.status
    record.manual_decision_by = reviewer.id
    record.manual_decision_remarks = payload.remarks
    log_action(
        db, vendor_id=record.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action="Manual credential decision",
        entity_type="CredentialVerification", entity_id=record.id, before_value=before, after_value=payload.status, details=payload.remarks,
    )
    db.commit()
    return {"message": "Decision recorded"}


@router.get("/profile-changes", response_model=list[ProfileChangeOut])
def list_pending_profile_changes(reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    changes = (
        db.query(ProfileChangeRequest)
        .filter(ProfileChangeRequest.status == "Submitted")
        .order_by(ProfileChangeRequest.server_date)
        .all()
    )
    out = []
    for change in changes:
        item = ProfileChangeOut.model_validate(change)
        vendor = db.query(Vendor).get(change.vendor_id)
        item.company_name = vendor.company_name if vendor else None
        out.append(item)
    return out


@router.post("/profile-changes/{change_id}/review")
def review_profile_change(change_id: int, payload: ReviewRequest, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    if payload.status not in ("Approved", "Rejected"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    change = db.query(ProfileChangeRequest).filter(ProfileChangeRequest.id == change_id).first()
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    if change.status != "Submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This change request was already decided")

    change.status = payload.status
    change.reviewed_by = reviewer.id
    change.review_remarks = payload.review_remarks
    change.reviewed_at = datetime.utcnow()

    if payload.status == "Approved":
        vendor = db.query(Vendor).filter(Vendor.id == change.vendor_id).first()
        setattr(vendor, change.field_name, change.new_value)
        vendor.profile_version += 1
        if change.field_name == "legal_name" and not vendor.trade_name:
            vendor.company_name = change.new_value

    log_action(
        db, vendor_id=change.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action=f"Profile change {payload.status.lower()}",
        entity_type="ProfileChangeRequest", entity_id=change.id, before_value=change.old_value, after_value=change.new_value,
    )
    notify(
        db, vendor_id=change.vendor_id, title=f"Profile change {payload.status.lower()}",
        message=f"Your request to change {change.field_name} has been {payload.status.lower()}.", category="Registration",
    )
    db.commit()
    return {"message": f"Profile change {payload.status.lower()}"}
