"""Masking helpers for sensitive fields (PAN, GSTIN, bank account, mobile,
email) shown in list/summary views and in audit-log snapshots, per
NFR-VEP-009. Detail views for an authorized viewer (the vendor themself,
or a reviewer looking at one application) show the full value instead."""


def mask_middle(value: str, keep_start: int = 2, keep_end: int = 2) -> str:
    if not value or len(value) <= keep_start + keep_end:
        return "*" * len(value or "")
    return value[:keep_start] + "*" * (len(value) - keep_start - keep_end) + value[-keep_end:]


def mask_pan(value: str) -> str:
    return mask_middle(value, 2, 2)


def mask_gstin(value: str) -> str:
    return mask_middle(value, 2, 2)


def mask_account_number(value: str) -> str:
    return mask_middle(value, 0, 4)


def mask_mobile(value: str) -> str:
    return mask_middle(value, 2, 2)


def mask_email(value: str) -> str:
    if not value or "@" not in value:
        return mask_middle(value or "")
    local, domain = value.split("@", 1)
    masked_local = local[0] + "*" * max(len(local) - 1, 1)
    return f"{masked_local}@{domain}"
