"""Simulated automatic credential verification (FR-VEP-002).

There is no real connection to the government PAN/GSTIN registries this
prototype could call, so this module stands in for that external system:
it applies the same format/checksum-style rules a real verification
service would reject on, and deterministically derives a result from the
vendor's own submitted data so the same vendor always gets the same
outcome. The record shape (CredentialVerification), the status values,
and the manual-review routing are the real ones the SRS describes --
only the "call out to a government database" step is faked.
"""

import re

from sqlalchemy.orm import Session

from app.events import log_action, notify
from app.models import CredentialVerification, Vendor

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]$")


def _simulate_check(credential_type: str, value: str, vendor: Vendor) -> tuple[str, str | None]:
    """Returns (status, mismatch_reason)."""
    pattern = PAN_PATTERN if credential_type == "PAN" else GSTIN_PATTERN
    if not pattern.match(value):
        return "Failed", f"{credential_type} does not match the expected format"

    # GSTIN's first two digits are a state code and characters 3-12 embed
    # the PAN -- a real registry would reject a GSTIN whose PAN segment
    # doesn't match the vendor's declared PAN. We can check that for free
    # without any external call.
    if credential_type == "GSTIN" and value[2:12] != vendor.pan_number:
        return "Mismatch", "GSTIN does not correspond to the vendor's declared PAN"

    # Deterministic "random" outcome so re-running verification for the
    # same vendor is stable: 1 in 20 goes to manual review, matching a
    # realistic small false-positive rate for this kind of check.
    if sum(ord(c) for c in value) % 20 == 0:
        return "Manual Review Required", "Automated source returned a low-confidence match"

    return "Verified", None


def run_credential_verification(db: Session, vendor: Vendor) -> list[CredentialVerification]:
    results = []
    for credential_type, value in (("PAN", vendor.pan_number), ("GSTIN", vendor.gstin_number)):
        status_value, mismatch_reason = _simulate_check(credential_type, value, vendor)
        record = CredentialVerification(
            vendor_id=vendor.id,
            credential_type=credential_type,
            reference_number=f"SIM-{credential_type}-{vendor.id}-{abs(hash(value)) % 100000}",
            status=status_value,
            mismatch_reason=mismatch_reason,
        )
        db.add(record)
        results.append(record)
        log_action(
            db, vendor_id=vendor.id, actor_id=None, actor_role="system",
            action=f"Credential verification ({credential_type})", entity_type="CredentialVerification",
            entity_id=None, after_value=status_value, details=mismatch_reason,
        )
        if status_value in ("Mismatch", "Failed", "Manual Review Required"):
            notify(
                db, vendor_id=vendor.id, title=f"{credential_type} verification needs attention",
                message=f"Automatic {credential_type} verification returned '{status_value}'. A reviewer will check it manually.",
                category="Registration",
            )
    return results
