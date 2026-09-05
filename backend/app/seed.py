"""One-time demo data so the portal is testable without first going
through the whole registration -> review -> approval pipeline by hand."""

from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Contract, ContractMilestone, CredentialVerification, Vendor, VendorDocument
from app.storage import UPLOAD_ROOT


def _minimal_pdf(label: str) -> bytes:
    """A tiny, valid, single-page PDF -- enough for a demo document that
    genuinely opens when downloaded, not just a placeholder filename."""
    text = f"({label} - demo document)"
    stream = f"BT /F1 14 Tf 40 60 Td {text} Tj ET".encode()
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 120]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream\nendobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF"
    )


def _demo_documents(vendor_id: int) -> list[VendorDocument]:
    """Writes real demo files to disk (same storage path convention as a
    real upload) and returns the VendorDocument rows for them, so the
    seeded approved vendor's Documents page isn't misleadingly empty."""
    folder = UPLOAD_ROOT / f"vendor_documents/{vendor_id}"
    folder.mkdir(parents=True, exist_ok=True)

    docs = [
        ("PAN card", "pan_card.pdf", "Verified"),
        ("GSTIN registration certificate", "gstin_certificate.pdf", "Verified"),
        ("Cancelled cheque / bank proof", "cancelled_cheque.pdf", "Verified"),
    ]
    rows = []
    for doc_type, file_name, verification_status in docs:
        stored_name = f"demo_{Path(file_name).stem}.pdf"
        (folder / stored_name).write_bytes(_minimal_pdf(doc_type))
        rows.append(
            VendorDocument(
                vendor_id=vendor_id,
                doc_type=doc_type,
                file_name=file_name,
                stored_path=f"vendor_documents/{vendor_id}/{stored_name}",
                verification_status=verification_status,
            )
        )
    return rows


def seed_demo_accounts(db: Session) -> None:
    if db.query(Vendor).count() > 0:
        return

    reviewer = Vendor(
        application_reference="APP-2026-00000",
        vendor_type="Service Provider",
        legal_name="GNCTD Procurement Cell",
        company_name="GNCTD Procurement Cell",
        contact_person_name="Reviewing Officer",
        email="reviewer@vendor.gov.in",
        mobile="9800000000",
        address="Delhi Secretariat, IP Estate, New Delhi",
        pan_number="AAAAA0000A",
        gstin_number="07AAAAA0000A1Z5",
        bank_account_number="000000000000",
        bank_ifsc="SBIN0000000",
        bank_name="State Bank of India",
        password_hash=hash_password("reviewer123"),
        role="reviewer",
        email_verified=True,
        mobile_verified=True,
        status="Approved",
    )
    db.add(reviewer)

    demo_vendor = Vendor(
        application_reference="APP-2026-00001",
        vendor_code="VEN-2026-10001",
        vendor_type="Supplier",
        legal_name="Shree Enterprises Private Limited",
        trade_name="Shree Enterprises",
        company_name="Shree Enterprises",
        contact_person_name="Ramesh Gupta",
        email="vendor1@example.com",
        mobile="9811111111",
        address="Karol Bagh, New Delhi - 110005",
        pan_number="ABCDE1234F",
        gstin_number="07ABCDE1234F1Z9",
        bank_account_number="123456789012",
        bank_ifsc="HDFC0001234",
        bank_name="HDFC Bank",
        password_hash=hash_password("vendor123"),
        role="vendor",
        email_verified=True,
        mobile_verified=True,
        status="Approved",
        submitted_at=datetime.utcnow() - timedelta(days=10),
        reviewed_at=datetime.utcnow() - timedelta(days=9),
    )
    db.add(demo_vendor)
    db.commit()
    db.refresh(demo_vendor)

    db.add_all(
        [
            CredentialVerification(
                vendor_id=demo_vendor.id,
                credential_type="PAN",
                reference_number="SIMPAN0001",
                status="Verified",
            ),
            CredentialVerification(
                vendor_id=demo_vendor.id,
                credential_type="GSTIN",
                reference_number="SIMGST0001",
                status="Verified",
            ),
        ]
    )

    db.add_all(_demo_documents(demo_vendor.id))

    contract = Contract(
        vendor_id=demo_vendor.id,
        contract_number="CON-2026-0001",
        po_number="PO-2026-0001",
        title="Supply of office stationery",
        description="Annual rate contract for supply of office stationery to GNCTD departments.",
        department="GNCTD Procurement Cell",
        payment_terms="Net 30 days from invoice approval",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=335),
        contract_value=500000,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    db.add_all(
        [
            ContractMilestone(
                contract_id=contract.id,
                title="Q1 supply batch",
                due_date=date.today() + timedelta(days=60),
                amount=125000,
            ),
            ContractMilestone(
                contract_id=contract.id,
                title="Q2 supply batch",
                due_date=date.today() + timedelta(days=150),
                amount=125000,
            ),
        ]
    )
    db.commit()
