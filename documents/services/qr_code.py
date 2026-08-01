# documents/services/qr_code.py
import qrcode
from io import BytesIO
from reportlab.platypus import Image
from reportlab.lib.units import cm

def generate_qr_image(data, width=2.5*cm, height=2.5*cm):
    """
    Return a ReportLab Image of a QR code encoding `data`.
    Default size increased to 2.5cm x 2.5cm.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,  # Increased for better readability
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E293B", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return Image(buffer, width=width, height=height)