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
    document_type = None

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
    # HEADER – Logo on right, company details on left
    # ------------------------------------------------------------
    def _build_header(self, story):
        company = self.company_data

        # ─── Left column: Company details ────────────────────
        left_content = [
            Paragraph(company['name'], self.styles['CompanyTitle']),
        ]
        if company['address']:
            left_content.append(Paragraph(company['address'], self.styles['Normal']))

        contact_parts = []
        if company['phone']:
            contact_parts.append(f"Tel: {company['phone']}")
        if company['email']:
            contact_parts.append(f"Email: {company['email']}")
        if company.get('website'):
            contact_parts.append(f"Web: {company['website']}")
        else:
            contact_parts.append("Web: www.jandn.mw")
        left_content.append(Paragraph(" | ".join(contact_parts), self.styles['Normal']))

        # ─── Right column: Logo (if exists) ──────────────────
        right_content = []
        if company.get('logo_path'):
            try:
                logo = Image(company['logo_path'], width=4*cm, height=2.5*cm)
                right_content.append(logo)
            except Exception:
                pass

        # ─── Build header table ──────────────────────────────
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
        story.append(Spacer(1, 0.3*cm))

        # ─── Document Title ──────────────────────────────────
        story.append(Paragraph(self.document_type.upper(), self.styles['DocTitle']))
        story.append(Spacer(1, 0.3*cm))

        # ─── Divider ──────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0')))
        story.append(Spacer(1, 0.3*cm))

        return story

    # ------------------------------------------------------------
    # FOOTER – Only "NB: This is not a taxed receipt." + QR code
    # ------------------------------------------------------------
    def _build_footer(self, story):
        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0')))
        story.append(Paragraph("NB: This is not a taxed receipt.", self.styles['Normal']))

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
        pass

    # ------------------------------------------------------------
    # Generation & Output
    # ------------------------------------------------------------
    def generate(self):
        story = []
        story = self._build_header(story)
        story = self.build_body(story)
        story = self._build_footer(story)
        self.doc.build(story)
        return self.buffer

    def get_pdf_bytes(self):
        if not self.buffer.getvalue():
            self.generate()
        self.buffer.seek(0)
        return self.buffer.getvalue()

    def render_to_response(self, filename=None):
        if not filename:
            filename = f"{self.document_type}_{self.object.reference}.pdf"
        response = HttpResponse(self.get_pdf_bytes(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def save_to_file(self, filepath):
        with open(filepath, 'wb') as f:
            f.write(self.get_pdf_bytes())

    def save_to_object(self):
        if hasattr(self.object, 'receipt_pdf'):
            field = self.object.receipt_pdf
            filename = f"{self.object.receipt_number or self.object.reference}.pdf"
        elif hasattr(self.object, 'pdf_file'):
            field = self.object.pdf_file
            filename = f"{self.object.reference}.pdf"
        else:
            return
        field.save(filename, ContentFile(self.get_pdf_bytes()))
        self.object.save()

    def email(self, recipient, subject=None, message=None, cc=None, bcc=None):
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
        email.attach(f"{self.object.reference}.pdf", self.get_pdf_bytes(), 'application/pdf')
        email.send()
