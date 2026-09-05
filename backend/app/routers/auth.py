import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_token, decode_token, get_current_vendor, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.events import log_action, notify
from app.masking import mask_email
from app.models import ROLES, VENDOR_TYPES, Vendor
from app.schemas import LoginRequest, LoginResponse, RegisterRequest, TokenResponse, VerifyOtpRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _generate_application_reference(db: Session) -> str:
    import datetime
    import random

    year = datetime.datetime.utcnow().year
    while True:
        candidate = f"APP-{year}-{random.randint(10000, 99999)}"
        if not db.query(Vendor).filter(Vendor.application_reference == candidate).first():
            return candidate


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.email == payload.email, Vendor.is_deleted.is_(False)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if not re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", payload.pan_number.upper()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PAN format is invalid (expected AAAAA9999A)")
    if not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]", payload.gstin_number.upper()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GSTIN format is invalid")

    role = payload.role if payload.role in ROLES else "vendor"
    vendor_type = payload.vendor_type if payload.vendor_type in VENDOR_TYPES else "Supplier"

    vendor = Vendor(
        application_reference=_generate_application_reference(db),
        vendor_type=vendor_type,
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        company_name=payload.trade_name or payload.legal_name,
        contact_person_name=payload.contact_person_name,
        email=payload.email,
        mobile=payload.mobile,
        address=payload.address,
        pan_number=payload.pan_number.upper(),
        gstin_number=payload.gstin_number.upper(),
        bank_account_number=payload.bank_account_number,
        bank_ifsc=payload.bank_ifsc,
        bank_name=payload.bank_name,
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=role, action="Registered", entity_type="Vendor", entity_id=vendor.id)
    notify(
        db,
        vendor_id=vendor.id,
        title="Welcome to the Vendor Portal",
        message="Your account has been created. Verify your email and mobile, upload your documents, and submit your registration for review.",
        category="Registration",
    )
    db.commit()

    return {"message": "Registration successful. You can now log in.", "application_reference": vendor.application_reference}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.email == payload.email, Vendor.is_deleted.is_(False)).first()
    if not vendor or not verify_password(payload.password, vendor.password_hash):
        log_action(
            db,
            vendor_id=vendor.id if vendor else None,
            actor_id=vendor.id if vendor else None,
            actor_role=vendor.role if vendor else None,
            action="Failed login",
            entity_type="Vendor",
            entity_id=vendor.id if vendor else None,
            result="Failure",
            details=f"Attempted login for {mask_email(payload.email)}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not vendor.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    pending_token = create_token(vendor.email, purpose="otp_pending", expires_minutes=5)
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Password verified", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    return LoginResponse(pending_token=pending_token)


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    if not payload.otp.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP must be 6 digits")

    email = decode_token(payload.pending_token, expected_purpose="otp_pending")
    vendor = db.query(Vendor).filter(Vendor.email == email, Vendor.is_deleted.is_(False)).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vendor not found")

    access_token = create_token(vendor.email, purpose="access", expires_minutes=settings.access_token_expire_minutes)
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Login", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    return TokenResponse(access_token=access_token)


@router.post("/logout")
def logout(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    log_action(db, vendor_id=vendor.id, actor_id=vendor.id, actor_role=vendor.role, action="Logout", entity_type="Vendor", entity_id=vendor.id)
    db.commit()
    return {"message": "Logged out"}
