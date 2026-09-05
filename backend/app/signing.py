"""Digital signing for generated PDFs.

This creates a self-signed certificate (once, cached on disk) and uses it to
apply a real cryptographic PDF signature (PKCS#7/CMS, the same mechanism a
government Digital Signature Certificate uses) to every document this app
issues. Opening a signed PDF in Adobe Reader will show a signature panel.

What this is NOT: the certificate is self-signed, not issued by a licensed
Certifying Authority (eMudhra, NIC, etc.) or backed by a hardware token, so
readers will show it as "not trusted" rather than a legally valid DSC. That
requires real CA infrastructure this prototype doesn't have. The signing
mechanism itself, however, is genuine.
"""

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from endesive.pdf import cms

KEYS_DIR = Path(__file__).parent / "keys"
KEY_PATH = KEYS_DIR / "signing_key.pem"
CERT_PATH = KEYS_DIR / "signing_cert.pem"

SIGNER_NAME = "Vendor Portal Signing Authority (Demo)"


def _generate_self_signed() -> None:
    KEYS_DIR.mkdir(exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Government of NCT of Delhi (Prototype)"),
            x509.NameAttribute(NameOID.COMMON_NAME, SIGNER_NAME),
        ]
    )
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )

    KEY_PATH.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _load_signing_identity():
    if not KEY_PATH.exists() or not CERT_PATH.exists():
        _generate_self_signed()
    key = serialization.load_pem_private_key(KEY_PATH.read_bytes(), password=None)
    cert = x509.load_pem_x509_certificate(CERT_PATH.read_bytes())
    return key, cert


_SIGNING_KEY, _SIGNING_CERT = _load_signing_identity()


def sign_pdf(pdf_bytes: bytes, reason: str) -> bytes:
    """Appends a real PKCS#7 signature to a PDF's bytes."""
    signing_dict = {
        "sigflags": 3,
        "contact": "helpdesk@example.gov.in",
        "location": "Delhi, India",
        "reason": reason,
        "signingdate": datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S+00'00'"),
    }
    signature = cms.sign(pdf_bytes, signing_dict, _SIGNING_KEY, _SIGNING_CERT, [], "sha256")
    return pdf_bytes + signature
