# documents/services/sales_order.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class SalesOrderPDFService(BasePDFService):
    document_type = 'sales_order'

    def _get_document_info(self):
        obj = self.object
        info = [
            Paragraph(f"Order #: {obj.reference}", self.styles['Normal']),
            Paragraph(f"Order Date: {obj.order_date.strftime('%d %B %Y')}", self.styles['Normal']),
        ]
        if obj.quotation:
            info.append(Paragraph(f"Quotation: {obj.quotation.reference}", self.styles['Normal']))
        return info

    def _get_customer_info(self):
        obj = self.object
        return [
            Paragraph("Customer:", self.styles['CompanyHeading']),
            Paragraph(obj.customer.name, self.styles['Normal']),
            Paragraph(obj.customer.address or '', self.styles['Normal']),
            Paragraph(obj.customer.phone or '', self.styles['Normal']),
            Paragraph(obj.customer.email or '', self.styles['Normal']),
        ]

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

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

        data = [['QTY', 'Description', 'Unit Price', 'Amount']]
        total = 0
        for item in obj.items.all():
            total += item.total
            data.append([
                f"{item.quantity} {item.item.unit.symbol}",
                item.item.name,
                f"{currency} {item.unit_price:.2f}",
                f"{currency} {item.total:.2f}",
            ])
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

        subtotal = obj.total_before_discount
        discount = obj.discount_amount or 0
        grand_total = subtotal - discount
        totals_data = [['Subtotal', f"{currency} {subtotal:.2f}"]]
        if discount > 0:
            totals_data.append(['Discount', f"{currency} {discount:.2f}"])
        totals_data.append(['Total', f"{currency} {grand_total:.2f}"])

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

        return story