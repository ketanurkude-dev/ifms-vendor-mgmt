from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditMixin:
    """Common columns every table should have. Add this to any new model."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    server_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    operation_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# Roles for approval workflow.
ROLES = ["vendor", "reviewer"]

VENDOR_TYPES = ["Supplier", "Contractor", "Consultant", "Service Provider"]

# Registration documents a vendor must upload before an application can be
# submitted, keyed by vendor type -- per FR-VEP-001's requirement that
# mandatory documents be configurable by vendor type.
MANDATORY_DOC_TYPES = {
    "Supplier": ["PAN card", "GSTIN registration certificate", "Cancelled cheque / bank proof"],
    "Contractor": [
        "PAN card",
        "GSTIN registration certificate",
        "Company registration certificate",
        "Cancelled cheque / bank proof",
    ],
    "Consultant": ["PAN card", "Cancelled cheque / bank proof"],
    "Service Provider": ["PAN card", "GSTIN registration certificate", "Cancelled cheque / bank proof"],
}

# Vendor fields that trigger a re-approval workflow (ProfileChangeRequest)
# instead of an immediate update, per FR-VEP-004.
CRITICAL_PROFILE_FIELDS = ["legal_name", "pan_number", "gstin_number", "bank_account_number", "bank_ifsc", "email", "mobile"]


class Vendor(AuditMixin, Base):
    """A registered vendor/supplier account. Registration goes through a
    review workflow (status) before the vendor can transact -- see
    VendorApplicationEvent for the history of that workflow."""

    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_reference: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    vendor_code: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)  # assigned on approval

    vendor_type: Mapped[str] = mapped_column(String(30), default="Supplier", nullable=False)
    legal_name: Mapped[str] = mapped_column(String(150), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)  # display name, defaults to legal_name
    contact_person_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)

    pan_number: Mapped[str] = mapped_column(String(10), nullable=False)
    gstin_number: Mapped[str] = mapped_column(String(15), nullable=False)
    bank_account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    bank_ifsc: Mapped[str] = mapped_column(String(15), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="vendor", nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(5), default="en", nullable=False)  # "en" | "hi"
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Dual OTP (email + mobile) verification, required before the
    # registration can be submitted for review.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mobile_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Draft -> Submitted -> Under Review -> Approved/Rejected/Returned
    status: Mapped[str] = mapped_column(String(30), default="Draft", nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class VendorDocument(AuditMixin, Base):
    """Registration documents uploaded by the vendor (PAN card, GSTIN
    certificate, registration certificate, cancelled cheque, etc)."""

    __tablename__ = "vendor_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(60), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # relative path on disk
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class VendorApplicationEvent(AuditMixin, Base):
    """One row per action taken on a vendor's registration application, so
    the full approval history can be shown to both the vendor and the
    reviewer."""

    __tablename__ = "vendor_application_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)


class CredentialVerification(AuditMixin, Base):
    """Result of checking a vendor's PAN/GSTIN/registration number against
    an external credential-verification source. Since no real government
    verification API is reachable from this prototype, the check is
    simulated by format/checksum-style rules -- but the record shape,
    statuses, and manual-override flow are the real ones per FR-VEP-002."""

    __tablename__ = "credential_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    credential_type: Mapped[str] = mapped_column(String(30), nullable=False)  # PAN | GSTIN
    source_system: Mapped[str] = mapped_column(String(60), default="Simulated Credential Registry", nullable=False)
    reference_number: Mapped[str] = mapped_column(String(60), nullable=False)
    response_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Verified | Mismatch | Failed | Pending | Not Available | Manual Review Required
    status: Mapped[str] = mapped_column(String(30), default="Pending", nullable=False)
    mismatch_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_decision_by: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    manual_decision_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProfileChangeRequest(AuditMixin, Base):
    """A vendor's request to change a critical profile field (legal name,
    PAN, GSTIN, bank details, email, mobile). Per FR-VEP-004, these fields
    require re-approval rather than an immediate update."""

    __tablename__ = "profile_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str] = mapped_column(String(255), nullable=False)
    new_value: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Submitted", nullable=False)  # Submitted|Approved|Rejected
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    review_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Contract(AuditMixin, Base):
    """A purchase order / contract issued to an approved vendor. Vendors
    can only raise invoices against a contract they hold."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    contract_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    po_number: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(150), default="GNCTD Procurement Cell", nullable=False)
    currency: Mapped[str] = mapped_column(String(5), default="INR", nullable=False)
    payment_terms: Mapped[str] = mapped_column(String(150), default="Net 30 days from invoice approval", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Active", nullable=False)  # Active|Completed|Terminated

    # Vendor-performance indicators, sourced from this portal itself since
    # there is no separate Contract Management module to integrate with --
    # kept as a single rating rather than the fuller KPI set in the SRS.
    performance_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    performance_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContractMilestone(AuditMixin, Base):
    __tablename__ = "contract_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)  # Pending|Completed|Delayed


class Invoice(AuditMixin, Base):
    """An invoice raised by a vendor against a contract, per the usual
    Submitted -> Under Review -> Approved/Rejected/Returned -> Paid
    lifecycle. A returned/rejected invoice may be corrected and
    re-submitted, keeping a link back to the one it replaces."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    bill_period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="Submitted", nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    review_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resubmitted_from_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)


class InvoiceDocument(AuditMixin, Base):
    """Supporting documents attached to an invoice (tax invoice, GRN,
    delivery challan, completion certificate, etc)."""

    __tablename__ = "invoice_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(60), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # relative path on disk
    verification_status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)


class Payment(AuditMixin, Base):
    """A payment made against an approved invoice. In place of a real
    banking-network integration, the reviewer simulates the bank's status
    update and callback through a dedicated action."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    payment_reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    mode_of_payment: Mapped[str] = mapped_column(String(30), default="Bank transfer", nullable=False)
    bank_reference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    response_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    response_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    callback_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciliation_status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)  # Pending|Matched|Exception
    # Initiated|Processing|Credited|Failed|Returned|Reversed
    status: Mapped[str] = mapped_column(String(20), default="Initiated", nullable=False)
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Notification(AuditMixin, Base):
    """In-app notification shown on the vendor's dashboard. No real
    email/SMS gateway is wired up -- rows are created directly by the
    workflow actions that would otherwise trigger a real notification."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="General", nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditLog(AuditMixin, Base):
    """Immutable trail of significant actions across the portal, per the
    SRS's audit-log requirement (Appendix C field list)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("vendors.id"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default="Success", nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
