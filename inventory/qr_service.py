import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
import json
import os


def generate_qr_code(item):
    """
    Generate a QR code for an inventory item.
    The QR code encodes a JSON payload with key item details.
    Scanning it gives the item's SKU, name, and unit instantly.
    """
    payload = json.dumps({
        "sku": item.sku,
        "name": item.name,
        "unit": item.unit.symbol,
        "category": item.category.name,
    })

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e293b", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f"qr_{item.sku.replace('/', '_')}.png"
    return ContentFile(buffer.read(), name=filename)


def generate_barcode(item):
    """
    Generate a Code128 barcode for an inventory item using the SKU.
    Returns a ContentFile suitable for saving to an ImageField.
    """
    # Clean SKU — barcode cannot have spaces or special chars
    sku_clean = item.sku.replace(' ', '-').replace('/', '-')

    try:
        code128 = barcode.get_barcode_class('code128')
        bc = code128(sku_clean, writer=ImageWriter())

        buffer = BytesIO()
        bc.write(buffer, options={
            'module_height': 15.0,
            'module_width': 0.4,
            'font_size': 10,
            'text_distance': 3.0,
            'quiet_zone': 4.0,
            'write_text': True,
        })
        buffer.seek(0)

        filename = f"barcode_{sku_clean}.png"
        return ContentFile(buffer.read(), name=filename)

    except Exception as e:
        return None


def generate_qr_and_barcode(item):
    """
    Generate both QR code and barcode for an item.
    Saves them to the item's ImageFields and saves the item.
    Called after item creation or on demand.
    """
    # QR Code
    qr_file = generate_qr_code(item)
    if item.qr_code:
        item.qr_code.delete(save=False)
    item.qr_code.save(qr_file.name, qr_file, save=False)

    # Barcode
    barcode_file = generate_barcode(item)
    if barcode_file and item.barcode_image:
        item.barcode_image.delete(save=False)
    if barcode_file:
        item.barcode_image.save(
            barcode_file.name, barcode_file, save=False
        )

    item.save()