# documents/services/sales_order.py

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class SalesOrderPDFService(BasePDFService):
    document_type = 'sales_order'

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        story.append(Paragraph("SALES ORDER", self.styles['CompanyHeading']))
        story.append(Paragraph(f"Order Number: {obj.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Date: {obj.order_date.strftime('%d %B %Y')}", self.styles['Normal']))
        if obj.quotation:
            story.append(Paragraph(f"Quotation: {obj.quotation.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Customer: {obj.customer.name}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # Items
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
        subtotal = obj.total_before_discount
        data.append(['', '', '', 'Subtotal', f"{subtotal:.2f}"])
        if obj.discount_amount > 0:
            data.append(['', '', '', 'Discount', f"-{obj.discount_amount:.2f}"])
        grand_total = subtotal - obj.discount_amount
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

        return story