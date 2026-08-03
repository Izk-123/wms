# documents/services/receipt.py
from .base import BasePDFService
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

class ReceiptPDFService(BasePDFService):
    document_type = 'receipt'

    def _get_document_info(self):
        payment = self.object
        return [
            Paragraph(f"Receipt #: {payment.receipt_number}", self.styles['Normal']),
            Paragraph(f"Payment Date: {payment.payment_date.strftime('%d %B %Y %H:%M')}", self.styles['Normal']),
            Paragraph(f"Invoice: {payment.invoice.reference}", self.styles['Normal']),
        ]

    def _get_customer_info(self):
        payment = self.object
        invoice = payment.invoice
        return [
            Paragraph("Received From:", self.styles['CompanyHeading']),
            Paragraph(invoice.customer.name, self.styles['Normal']),
            Paragraph(invoice.customer.address or '', self.styles['Normal']),
            Paragraph(invoice.customer.phone or '', self.styles['Normal']),
            Paragraph(invoice.customer.email or '', self.styles['Normal']),
        ]

    def build_body(self, story):
        payment = self.object
        invoice = payment.invoice
        currency = self.company_data['currency']
        receiver = payment.received_by.get_full_name() or payment.received_by.username

        # Info table
        info_data = [[self._get_document_info(), self._get_customer_info()]]
        info_table = Table(info_data, colWidths=[8*cm, 8*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (1,0), (1,0), 0),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        # Payment details
        data = [
            ['Payment Method', payment.get_payment_method_display()],
            ['Amount Paid', f"{currency} {payment.amount:.2f}"],
            ['Balance Due', f"{currency} {invoice.balance_due:.2f}"],
            ['Received By', receiver],
        ]
        table = Table(data, colWidths=[5*cm, 8.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('BACKGROUND', (0,1), (1,1), colors.HexColor('#F1F5F9')),
            ('BACKGROUND', (0,2), (1,2), colors.white),
            ('BACKGROUND', (0,3), (1,3), colors.HexColor('#F1F5F9')),
        ]))
        story.append(table)

        return story