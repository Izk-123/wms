# documents/services/invoice.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService
from company_settings.services import get_setting

class InvoicePDFService(BasePDFService):
    document_type = 'invoice'

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        # ---- Title & metadata ----
        story.append(Paragraph("INVOICE", self.styles['CompanyHeading']))
        story.append(Paragraph(f"Reference: {obj.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Date: {obj.invoice_date.strftime('%d %B %Y')}", self.styles['Normal']))
        story.append(Paragraph(f"Due Date: {obj.due_date.strftime('%d %B %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # ---- Customer ----
        story.append(Paragraph("Bill To:", self.styles['CompanyHeading']))
        story.append(Paragraph(obj.customer.name, self.styles['Normal']))
        if obj.customer.address:
            story.append(Paragraph(obj.customer.address, self.styles['Normal']))
        if obj.customer.phone:
            story.append(Paragraph(f"Phone: {obj.customer.phone}", self.styles['Normal']))
        if obj.customer.email:
            story.append(Paragraph(f"Email: {obj.customer.email}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # ---- Items table ----
        data = [['#', 'Item', 'Qty', 'Unit Price', 'Total']]
        for idx, item in enumerate(obj.items.all(), 1):
            data.append([
                str(idx),
                item.item.name,
                f"{item.quantity} {item.item.unit.symbol}",
                f"{item.unit_price:.2f}",
                f"{item.total:.2f}",
            ])

        # Totals
        subtotal = obj.total_amount
        data.append(['', '', '', 'Subtotal', f"{subtotal:.2f}"])
        discount = obj.sales_order.discount_amount if obj.sales_order else 0
        if discount > 0:
            data.append(['', '', '', 'Discount', f"-{discount:.2f}"])
        grand_total = subtotal - discount
        data.append(['', '', '', 'Total', f"{grand_total:.2f}"])

        col_widths = [1*cm, 6*cm, 3*cm, 3*cm, 3*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0,1), (-1,-2), colors.white),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (1,1), (-1,-1), 'LEFT'),
            ('ALIGN', (2,1), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (3,-1), (-1,-1), 'RIGHT'),
        ]))
        story.append(table)

        # ---- Payment terms ----
        story.append(Spacer(1, 0.5*cm))
        terms = get_setting('DEFAULT_PAYMENT_TERMS', 'Net 30')
        story.append(Paragraph(f"Payment Terms: {terms}", self.styles['Normal']))

        return story