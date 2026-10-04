import re
from urllib.parse import quote

def is_valid_upi_id(upi_id: str) -> bool:
    """Validates basic UPI ID format (e.g., username@bankname)."""
    if not upi_id or not isinstance(upi_id, str):
        return False
    return bool(re.match(r"^[\w\.\-]+@[\w\-]+$", upi_id.strip()))

def build_upi_link(upi_id: str, payee_name: str, amount: float, note: str = "SplitSnap bill") -> str:
    """Constructs a standard upi://pay URI."""
    encoded_name = quote(payee_name or "")
    encoded_note = quote(note or "")
    return f"upi://pay?pa={quote(upi_id.strip())}&pn={encoded_name}&am={amount:.2f}&cu=INR&tn={encoded_note}"

def make_qr_png(data: str):
    """Generates QR code PNG bytes if qrcode package is available, else returns None."""
    try:
        import qrcode
        import io
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None
