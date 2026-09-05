from datetime import date, datetime

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    vendor_type: str = "Supplier"  # Supplier | Contractor | Consultant | Service Provider
    legal_name: str = Field(min_length=2, max_length=150)
    trade_name: str | None = None
    contact_person_name: str
    email: str
    mobile: str = Field(min_length=10, max_length=15)
    address: str
    pan_number: str = Field(min_length=10, max_length=10)
    gstin_number: str = Field(min_length=15, max_length=15)
    bank_account_number: str
    bank_ifsc: str
    bank_name: str
    password: str = Field(min_length=6)
    role: str = "vendor"  # "vendor" | "reviewer" -- lets a demo reviewer account be created


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    pending_token: str
    message: str = "Password verified. Enter the OTP sent to your registered mobile."


class VerifyOtpRequest(BaseModel):
    pending_token: str
    otp: str = Field(min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VendorOut(BaseModel):
    id: int
    application_reference: str
    vendor_code: str | None
    vendor_type: str
    legal_name: str
    trade_name: str | None
    company_name: str
    contact_person_name: str
    email: str
    mobile: str
    address: str
    pan_number: str
    gstin_number: str
    bank_account_number: str
    bank_ifsc: str
    bank_name: str
    role: str
    preferred_language: str
    profile_version: int
    email_verified: bool
    mobile_verified: bool
    status: str
    submitted_at: datetime | None
    review_remarks: str | None

    class Config:
        from_attributes = True


class LanguageUpdate(BaseModel):
    language: str  # "en" | "hi"


class OtpRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6)


class VendorDocumentOut(BaseModel):
    id: int
    doc_type: str
    file_name: str
    has_file: bool = False
    version: int
    expiry_date: date | None
    verification_status: str
    remarks: str | None
    server_date: datetime

    class Config:
        from_attributes = True


class VendorApplicationEventOut(BaseModel):
    action: str
    remarks: str | None
    server_date: datetime

    class Config:
        from_attributes = True


class CredentialVerificationOut(BaseModel):
    id: int
    credential_type: str
    source_system: str
    reference_number: str
    response_timestamp: datetime
    status: str
    mismatch_reason: str | None
    manual_decision_remarks: str | None

    class Config:
        from_attributes = True


class ManualVerificationDecision(BaseModel):
    status: str  # Verified | Mismatch | Failed | Manual Review Required
    remarks: str | None = None


class ApplicationDetailOut(BaseModel):
    vendor: VendorOut
    documents: list[VendorDocumentOut]
    events: list[VendorApplicationEventOut]
    credential_verifications: list[CredentialVerificationOut]


class ApplicationQueueItem(BaseModel):
    id: int
    application_reference: str
    vendor_type: str
    company_name: str
    contact_person_name: str
    email: str
    mobile: str
    address: str
    pan_number: str
    gstin_number: str
    status: str
    submitted_at: datetime | None
    server_date: datetime


class ReviewRequest(BaseModel):
    status: str  # "Approved" | "Rejected" | "Returned"
    review_remarks: str | None = None


class DocumentReviewRequest(BaseModel):
    verification_status: str  # "Verified" | "Rejected"
    remarks: str | None = None


class ProfileUpdate(BaseModel):
    """Non-critical profile fields the vendor may update directly."""

    trade_name: str | None = None
    contact_person_name: str | None = None
    address: str | None = None
    bank_name: str | None = None


class ProfileChangeCreate(BaseModel):
    field_name: str  # one of CRITICAL_PROFILE_FIELDS
    new_value: str
    reason: str = Field(min_length=5)


class ProfileChangeOut(BaseModel):
    id: int
    vendor_id: int
    company_name: str | None = None
    field_name: str
    old_value: str
    new_value: str
    reason: str
    status: str
    review_remarks: str | None
    reviewed_at: datetime | None
    server_date: datetime

    class Config:
        from_attributes = True


class PendingAction(BaseModel):
    kind: str
    message: str


class VendorDashboardOut(BaseModel):
    vendor: VendorOut
    profile_completeness_percent: int
    pending_actions: list[PendingAction]
    invoice_summary: dict[str, int]
    payment_summary: dict[str, str | float | int]
    contract_count: int


class ContractMilestoneCreate(BaseModel):
    title: str
    due_date: date
    amount: float


class ContractMilestoneUpdate(BaseModel):
    status: str  # Pending | Completed | Delayed


class ContractMilestoneOut(BaseModel):
    id: int
    title: str
    due_date: date
    amount: float
    status: str

    class Config:
        from_attributes = True


class ContractCreate(BaseModel):
    vendor_id: int
    contract_number: str
    po_number: str
    title: str = Field(min_length=3)
    description: str
    department: str = "GNCTD Procurement Cell"
    currency: str = "INR"
    payment_terms: str = "Net 30 days from invoice approval"
    start_date: date
    end_date: date
    contract_value: float


class ContractPerformanceUpdate(BaseModel):
    performance_rating: int = Field(ge=1, le=5)
    performance_remarks: str | None = None


class ContractOut(BaseModel):
    id: int
    vendor_id: int
    contract_number: str
    po_number: str
    title: str
    description: str
    department: str
    currency: str
    payment_terms: str
    start_date: date
    end_date: date
    contract_value: float
    status: str
    performance_rating: int | None
    performance_remarks: str | None
    operation_date: datetime
    milestones: list[ContractMilestoneOut] = []
    remaining_value: float = 0

    class Config:
        from_attributes = True


class InvoiceDocumentOut(BaseModel):
    id: int
    doc_type: str
    file_name: str
    has_file: bool = False
    verification_status: str

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    contract_id: int
    invoice_number: str
    invoice_date: date
    bill_period: str | None = None
    description: str
    amount: float
    tax_amount: float = 0


class InvoiceOut(BaseModel):
    id: int
    vendor_id: int
    contract_id: int
    invoice_number: str
    invoice_date: date
    bill_period: str | None
    description: str
    amount: float
    tax_amount: float
    total_amount: float
    status: str
    review_remarks: str | None
    reviewed_at: datetime | None
    server_date: datetime
    resubmitted_from_id: int | None
    documents: list[InvoiceDocumentOut] = []

    class Config:
        from_attributes = True


class PaymentInitiate(BaseModel):
    mode_of_payment: str = "Bank transfer"


class PaymentStatusUpdate(BaseModel):
    status: str  # "Processing" | "Credited" | "Failed" | "Returned" | "Reversed"
    bank_reference: str | None = None
    response_code: str | None = None
    response_message: str | None = None


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    invoice_number: str = ""
    payment_reference: str
    amount: float
    mode_of_payment: str
    bank_reference: str | None
    response_code: str | None
    response_message: str | None
    callback_timestamp: datetime | None
    reconciliation_status: str
    status: str
    expected_completion_date: date | None = None
    processed_at: datetime | None
    server_date: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    category: str
    is_read: bool
    server_date: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    vendor_id: int | None
    actor_id: int | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: int | None
    before_value: str | None
    after_value: str | None
    result: str
    correlation_id: str | None
    details: str | None
    server_date: datetime

    class Config:
        from_attributes = True
