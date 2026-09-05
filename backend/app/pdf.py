"""PDF generation for the Vendor Portal. Uses the Noto Sans Devanagari
font for both English and Hindi text so a single font family renders
either language without a metrics mismatch -- same approach used in the
other two IFMS portals."""

from pathlib import Path

from fpdf import FPDF

from app.signing import SIGNER_NAME, sign_pdf

FONTS_DIR = Path(__file__).parent / "fonts"

PDF_HI = {
    "Payment Advice": "भुगतान सलाह",
    "Vendor": "विक्रेता",
    "Vendor Code": "विक्रेता कोड",
    "Invoice Number": "चालान संख्या",
    "Payment Reference": "भुगतान संदर्भ",
    "Payment Date": "भुगतान तिथि",
    "Amount": "राशि",
    "Bank Reference": "बैंक संदर्भ",
    "Status": "स्थिति",
    "This is a system-generated document.": "यह एक सिस्टम-जनित दस्तावेज़ है।",
}


def _t(language: str, key: str) -> str:
    if language == "hi":
        return PDF_HI.get(key, key)
    return key


class _Pdf(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Noto", "", str(FONTS_DIR / "NotoSansDevanagari.ttf"))
        self.add_font("Noto", "B", str(FONTS_DIR / "NotoSansDevanagari-Bold.ttf"))
        self.add_font("Noto", "I", str(FONTS_DIR / "NotoSansDevanagari.ttf"))


def build_payment_advice_pdf(payment, invoice, vendor, language: str = "en") -> bytes:
    pdf = _Pdf()
    pdf.add_page()
    pdf.set_font("Noto", "B", 16)
    pdf.cell(0, 10, _t(language, "Payment Advice"), ln=True)
    pdf.set_font("Noto", "", 10)
    pdf.cell(0, 6, "Government of NCT of Delhi -- Vendor Portal (Prototype)", ln=True)
    pdf.ln(6)

    rows = [
        (_t(language, "Vendor"), vendor.company_name),
        (_t(language, "Vendor Code"), vendor.vendor_code or "-"),
        (_t(language, "Invoice Number"), invoice.invoice_number),
        (_t(language, "Payment Reference"), payment.payment_reference),
        (_t(language, "Payment Date"), str(payment.processed_at or payment.server_date)[:19]),
        (_t(language, "Amount"), f"Rs. {payment.amount}"),
        (_t(language, "Bank Reference"), payment.bank_reference or "-"),
        (_t(language, "Status"), payment.status),
    ]
    pdf.set_font("Noto", "", 11)
    for label, value in rows:
        pdf.cell(60, 8, str(label), border=1)
        pdf.cell(0, 8, str(value), border=1, ln=True)

    pdf.ln(10)
    pdf.set_font("Noto", "I", 9)
    pdf.multi_cell(0, 5, _t(language, "This is a system-generated document."))

    pdf_bytes = bytes(pdf.output())
    return sign_pdf(pdf_bytes, reason=f"Payment advice issued by {SIGNER_NAME}")
