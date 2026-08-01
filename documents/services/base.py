# documents/services/base.py
from abc import ABC, abstractmethod
from io import BytesIO
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, HRFlowable, Table, TableStyle
from .branding import get_company_data, get_document_styles
from .qr_code import generate_qr_image
from company_settings.services import get_setting

class BasePDFService(ABC):
    """
    Abstract base class for all PDF document services.
    Subclasses must set document_type and implement build_body().
    """

    document_type = None  # Override in subclasses (e.g., 'invoice', 'receipt')

    def __init__(self, document_object):
        self.object = document_object
        self.company_data = get_company_data()
        self.styles = get_document_styles()
        self.buffer = BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=1.5*cm,
        )

    # ------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------
    def _build_header(self, story):
        """
        Build professional header with:
        - Logo on the right
        - Company name and contact on the left
        - Customer details on the right
        - Document title and metadata
        """
        company = self.company_data
        obj = self.object

        # ─── TOP SECTION: Company Logo + Info ──────────────────────
        # Left column: Company info
        left_content = [
            Paragraph(company['name'], self.styles['CompanyTitle']),
            Paragraph(company['address'], self.styles['Normal']),
        ]

        # Right column: Logo (if exists)
        right_content = []
        if company['logo_path']:
            try:
                logo = Image(company['logo_path'], width=4.5*cm, height=3*cm)
                right_content.append(logo)
            except Exception:
                pass

        # Build header table
        header_data = [[
            left_content,
            right_content
        ]]
        header_table = Table(header_data, colWidths=[12*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 0.5*cm))

        # ─── DIVIDER LINE ───────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E293B')))
        story.append(Spacer(1, 0.3*cm))

        # ─── DOCUMENT TITLE ─────────────────────────────────────────
        story.append(Paragraph(self.document_type.upper(), self.styles['DocTitle']))
        story.append(Spacer(1, 0.3*cm))

        # ─── DOCUMENT METADATA (Reference, Date, etc.) ─────────────
        # Left: Document info, Right: Customer info
        doc_info = self._get_document_info()
        customer_info = self._get_customer_info()

        info_table_data = [[
            doc_info,
            customer_info
        ]]
        info_table = Table(info_table_data, colWidths=[9*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        return story

    def _get_document_info(self):
        """Override in subclasses to return document-specific info."""
        return []

    def _get_customer_info(self):
        """Override in subclasses to return customer-specific info."""
        return []

    def _build_footer(self, story):
        """Add footer with contact details and QR code."""
        company = self.company_data

        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))

        # ─── FOOTER MESSAGE (updated) ──────────────────────────────
        story.append(Paragraph("NB: This is not a taxed receipt.", self.styles['Normal']))
        story.append(Spacer(1, 0.3*cm))

        # ─── TERMS AND CONDITIONS ────────────────────────────────────
        story.append(Paragraph("TERMS AND CONDITIONS", self.styles['CompanyHeading']))
        story.append(Paragraph("Payment is due within 14 days of project completion.", self.styles['Normal']))
        story.append(Paragraph("All checks to be made out to the company name above.", self.styles['Normal']))
        story.append(Spacer(1, 0.3*cm))

        # ─── FOOTER WITH CONTACT & QR ──────────────────────────────
        footer_data = [[
            Paragraph(f"Tel: {company['phone']}", self.styles['Normal']),
            Paragraph(f"Email: {company['email']}", self.styles['Normal']),
            Paragraph(f"Web: {company.get('website', 'www.jandn.mw')}", self.styles['Normal']),
        ]]
        footer_table = Table(footer_data, colWidths=[5*cm, 5*cm, 5*cm])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(footer_table)

        # ─── QR Code (bottom right) ──────────────────────────────────
        qr_data = {
            'doc_type': self.document_type,
            'reference': self.object.reference,
            'company': self.company_data['name'],
            'date': str(getattr(self.object, 'created_at', None) or
                       getattr(self.object, 'invoice_date', None) or
                       getattr(self.object, 'payment_date', None) or
                       '')
        }
        qr_img = generate_qr_image(qr_data, width=2.5*cm, height=2.5*cm)
        story.append(Spacer(1, 0.3*cm))
        story.append(qr_img)

        return story

    @abstractmethod
    def build_body(self, story):
        """Build the main content of the document. Must be implemented by subclasses."""
        pass

    # ------------------------------------------------------------
    # Generation & Output
    # ------------------------------------------------------------
    def generate(self):
        """Generate the PDF document and return the BytesIO buffer."""
        story = []
        story = self._build_header(story)
        story = self.build_body(story)
        story = self._build_footer(story)
        self.doc.build(story)
        return self.buffer

    def get_pdf_bytes(self):
        """Return the PDF as bytes."""
        if not self.buffer.getvalue():
            self.generate()
        self.buffer.seek(0)
        return self.buffer.getvalue()

    def render_to_response(self, filename=None):
        """Return a Django HttpResponse with the PDF."""
        if not filename:
            filename = f"{self.document_type}_{self.object.reference}.pdf"
        response = HttpResponse(self.get_pdf_bytes(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def save_to_file(self, filepath):
        """Save the PDF to a local file path."""
        with open(filepath, 'wb') as f:
            f.write(self.get_pdf_bytes())

    def save_to_object(self):
        """
        Save the PDF to the object's 'pdf_file' field (if it exists).
        This method assumes the model has a FileField named 'pdf_file'.
        """
        if not hasattr(self.object, 'pdf_file'):
            # For receipts, the field might be called 'receipt_pdf'
            if hasattr(self.object, 'receipt_pdf'):
                field = getattr(self.object, 'receipt_pdf')
                filename = f"{self.object.receipt_number or self.object.reference}.pdf"
            else:
                # If no field found, skip silently
                return
        else:
            field = getattr(self.object, 'pdf_file')
            filename = f"{self.object.reference}.pdf"

        field.save(filename, ContentFile(self.get_pdf_bytes()))
        self.object.save()

    # ------------------------------------------------------------
    # Email
    # ------------------------------------------------------------
    def email(self, recipient, subject=None, message=None, cc=None, bcc=None):
        """
        Email the PDF as an attachment.
        """
        if not subject:
            subject = f"{self.document_type.title()} {self.object.reference}"
        if not message:
            message = f"Please find attached your {self.document_type}."

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=get_setting('DEFAULT_FROM_EMAIL', 'noreply@jandn.mw'),
            to=[recipient] if isinstance(recipient, str) else recipient,
            cc=cc,
            bcc=bcc,
        )
        attachment_name = f"{self.object.reference}.pdf"
        email.attach(attachment_name, self.get_pdf_bytes(), 'application/pdf')
        email.send()