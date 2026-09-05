from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor, require_reviewer
from app.database import get_db
from app.events import log_action, notify
from app.models import Contract, Invoice, InvoiceDocument, Vendor
from app.routers.contracts import invoiced_amount
from app.schemas import InvoiceCreate, InvoiceDocumentOut, InvoiceOut, ReviewRequest
from app.storage import guess_media_type, read_stored_file, save_upload, validate_upload

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _doc_out(document: InvoiceDocument) -> InvoiceDocumentOut:
    out = InvoiceDocumentOut.model_validate(document)
    out.has_file = bool(document.stored_path)
    return out


def _to_out(invoice: Invoice, db: Session) -> InvoiceOut:
    documents = (
        db.query(InvoiceDocument)
        .filter(InvoiceDocument.invoice_id == invoice.id, InvoiceDocument.is_deleted.is_(False))
        .all()
    )
    out = InvoiceOut.model_validate(invoice)
    out.documents = [_doc_out(d) for d in documents]
    return out


@router.get("", response_model=list[InvoiceOut])
def list_invoices(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """A reviewer sees every invoice; a vendor sees only their own."""
    query = db.query(Invoice).filter(Invoice.is_deleted.is_(False))
    if vendor.role != "reviewer":
        query = query.filter(Invoice.vendor_id == vendor.id)
    invoices = query.order_by(Invoice.server_date.desc()).all()
    return [_to_out(i, db) for i in invoices]


def _check_duplicate(db: Session, vendor_id: int, payload: InvoiceCreate) -> None:
    """Per FR-VEP-006: flag likely-duplicate invoices using vendor,
    invoice number, invoice date, contract reference, and amount."""
    duplicate = (
        db.query(Invoice)
        .filter(
            Invoice.vendor_id == vendor_id,
            Invoice.contract_id == payload.contract_id,
            Invoice.invoice_date == payload.invoice_date,
            Invoice.amount == payload.amount,
            Invoice.is_deleted.is_(False),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A similar invoice already exists ({duplicate.invoice_number}) for this contract, date, and amount",
        )


def _validate_against_contract(db: Session, contract: Contract, payload: InvoiceCreate) -> None:
    """Per FR-VEP-006: validate the invoice date falls within the
    contract's validity period, and that raising it wouldn't exceed the
    contract's remaining payable value -- our stand-in for validating
    against the source procurement/PO system, since there is no
    separate PO-line-item model in this prototype."""
    if not (contract.start_date <= payload.invoice_date <= contract.end_date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice date must fall within the contract's validity period ({contract.start_date} to {contract.end_date})",
        )

    total_amount = payload.amount + payload.tax_amount
    already_invoiced = invoiced_amount(db, contract.id)
    remaining = float(contract.contract_value) - already_invoiced
    if total_amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice amount (Rs. {total_amount}) exceeds the contract's remaining payable value (Rs. {remaining})",
        )


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if vendor.status != "Approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an approved vendor can raise invoices")

    contract = (
        db.query(Contract)
        .filter(Contract.id == payload.contract_id, Contract.vendor_id == vendor.id, Contract.is_deleted.is_(False))
        .first()
    )
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    if contract.status != "Active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoices can only be raised against an active contract")

    _check_duplicate(db, vendor.id, payload)
    _validate_against_contract(db, contract, payload)

    invoice = Invoice(
        vendor_id=vendor.id, contract_id=contract.id, invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date, bill_period=payload.bill_period, description=payload.description,
        amount=payload.amount, tax_amount=payload.tax_amount, total_amount=payload.amount + payload.tax_amount,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Invoice submitted", entity_type="Invoice", entity_id=invoice.id)
    db.commit()
    return _to_out(invoice, db)


@router.post("/{invoice_id}/resubmit", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def resubmit_invoice(invoice_id: int, payload: InvoiceCreate, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """Per FR-VEP-006: a returned/rejected invoice can be corrected and
    resubmitted as a new invoice that keeps a link to the original."""
    original = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.vendor_id == vendor.id).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if original.status not in ("Rejected", "Returned"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a rejected or returned invoice can be resubmitted")

    contract = db.query(Contract).filter(Contract.id == payload.contract_id, Contract.vendor_id == vendor.id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    _validate_against_contract(db, contract, payload)

    new_invoice = Invoice(
        vendor_id=vendor.id, contract_id=payload.contract_id, invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date, bill_period=payload.bill_period, description=payload.description,
        amount=payload.amount, tax_amount=payload.tax_amount, total_amount=payload.amount + payload.tax_amount,
        resubmitted_from_id=original.id,
    )
    db.add(new_invoice)
    log_action(
        db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Invoice resubmitted",
        entity_type="Invoice", entity_id=None, before_value=original.invoice_number,
    )
    db.commit()
    db.refresh(new_invoice)
    return _to_out(new_invoice, db)


@router.post("/{invoice_id}/documents", response_model=InvoiceDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_invoice_document(
    invoice_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.vendor_id == vendor.id).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    validate_upload(file)
    contents = await file.read()
    stored_path = save_upload(file, f"invoice_documents/{invoice_id}", contents)

    document = InvoiceDocument(invoice_id=invoice_id, doc_type=doc_type, file_name=file.filename, stored_path=stored_path)
    db.add(document)
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Invoice document uploaded", entity_type="InvoiceDocument", entity_id=None, after_value=doc_type)
    db.commit()
    db.refresh(document)
    return _doc_out(document)


@router.get("/documents/{document_id}/download")
def download_invoice_document(document_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    document = db.query(InvoiceDocument).filter(InvoiceDocument.id == document_id).first()
    if not document or not document.stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    invoice = db.query(Invoice).filter(Invoice.id == document.invoice_id).first()
    if vendor.role != "reviewer" and invoice.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document")

    contents = read_stored_file(document.stored_path)
    return Response(content=contents, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={document.file_name}"})


@router.get("/documents/{document_id}/view")
def view_invoice_document(document_id: int, vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    """Same file as /download, but served inline with the real content
    type so a browser tab can render the PDF/image instead of saving it."""
    document = db.query(InvoiceDocument).filter(InvoiceDocument.id == document_id).first()
    if not document or not document.stored_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    invoice = db.query(Invoice).filter(Invoice.id == document.invoice_id).first()
    if vendor.role != "reviewer" and invoice.vendor_id != vendor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this document")

    contents = read_stored_file(document.stored_path)
    media_type = guess_media_type(document.file_name)
    return Response(content=contents, media_type=media_type, headers={"Content-Disposition": f"inline; filename={document.file_name}"})


@router.post("/{invoice_id}/review", response_model=InvoiceOut)
def review_invoice(invoice_id: int, payload: ReviewRequest, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    if payload.status not in ("Approved", "Rejected", "Returned"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.is_deleted.is_(False)).first()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status != "Submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only a submitted invoice can be reviewed")
    if payload.status in ("Rejected", "Returned") and not payload.review_remarks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Remarks are required to reject or return an invoice")

    invoice.status = payload.status
    invoice.reviewed_by = reviewer.id
    invoice.review_remarks = payload.review_remarks
    invoice.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(invoice)

    log_action(db, vendor_id=invoice.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action=f"Invoice {payload.status.lower()}", entity_type="Invoice", entity_id=invoice.id, before_value="Submitted", after_value=payload.status)
    notify(
        db, vendor_id=invoice.vendor_id, title=f"Invoice {payload.status.lower()}",
        message=f"Invoice {invoice.invoice_number} has been {payload.status.lower()}.", category="Invoice",
    )
    db.commit()
    return _to_out(invoice, db)
