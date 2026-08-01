# documents/services/invoice.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService
from company_settings.services import get_setting

class InvoicePDFService(BasePDFService):
    document_type = 'invoice'

    def _get_document_info(self):
        """Return invoice-specific document info (left column)."""
        obj = self.object
        return [
            Paragraph(f"Invoice #: {obj.reference}", self.styles['Normal']),
            Paragraph(f"Invoice Date: {obj.invoice_date.strftime('%d %B %Y')}", self.styles['Normal']),
            Paragraph(f"Due Date: {obj.due_date.strftime('%d %B %Y')}", self.styles['Normal']),
        ]

    def _get_customer_info(self):
        """Return customer info (right column)."""
        obj = self.object
        return [
            Paragraph("Bill To:", self.styles['CompanyHeading']),
            Paragraph(obj.customer.name, self.styles['Normal']),
            Paragraph(obj.customer.address or '', self.styles['Normal']),
            Paragraph(obj.customer.phone or '', self.styles['Normal']),
            Paragraph(obj.customer.email or '', self.styles['Normal']),
        ]

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        # ─── ITEMS TABLE ─────────────────────────────────────────────
        data = [['QTY', 'Description', 'Unit Price', 'Amount']]
        total_amount = 0

        for idx, item in enumerate(obj.items.all(), 1):
            item_total = item.total
            total_amount += item_total
            data.append([
                f"{item.quantity} {item.item.unit.symbol}",
                item.item.name,
                f"{currency} {item.unit_price:.2f}",
                f"{currency} {item_total:.2f}",
            ])

        # Add empty rows if needed (minimum 5 rows for consistent height)
        while len(data) < 6:
            data.append(['', '', '', ''])

        col_widths = [2.5*cm, 7*cm, 3.5*cm, 3.5*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
            ('ALIGN', (3,1), (-1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

        # ─── TOTALS SECTION ──────────────────────────────────────────
        subtotal = obj.total_amount
        discount = obj.sales_order.discount_amount if obj.sales_order else 0
        tax = 0  # Tax not implemented yet
        grand_total = subtotal - discount

        totals_data = [
            ['Subtotal', f"{currency} {subtotal:.2f}"],
            ['Sales Tax (5%)', f"{currency} {tax:.2f}"],
            ['Discount', f"{currency} {discount:.2f}"],
            ['Total', f"{currency} {grand_total:.2f}"],
        ]

        totals_table = Table(totals_data, colWidths=[7*cm, 6.5*cm])
        totals_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('FONTNAME', (0,-1), (1,-1), 'Helvetica-Bold'),
            ('BACKGROUND', (0,-1), (1,-1), colors.HexColor('#F1F5F9')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(totals_table)

        # ─── PAYMENT TERMS ────────────────────────────────────────────
        story.append(Spacer(1, 0.5*cm))
        terms = get_setting('DEFAULT_PAYMENT_TERMS', 'Net 30')
        story.append(Paragraph(f"Payment Terms: {terms}", self.styles['Normal']))

        return story