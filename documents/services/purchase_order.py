# documents/services/purchase_order.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class PurchaseOrderPDFService(BasePDFService):
    document_type = 'purchase_order'

    def _get_document_info(self):
        obj = self.object
        return [
            Paragraph(f"PO #: {obj.reference}", self.styles['Normal']),
            Paragraph(f"Date: {obj.created_at.strftime('%d %B %Y')}", self.styles['Normal']),
            Paragraph(f"Expected Delivery: {obj.expected_delivery.strftime('%d %B %Y') if obj.expected_delivery else 'TBD'}", self.styles['Normal']),
        ]

    def _get_customer_info(self):
        obj = self.object
        return [
            Paragraph("Supplier:", self.styles['CompanyHeading']),
            Paragraph(obj.supplier.name, self.styles['Normal']),
            Paragraph(obj.supplier.address or '', self.styles['Normal']),
            Paragraph(obj.supplier.phone or '', self.styles['Normal']),
            Paragraph(obj.supplier.email or '', self.styles['Normal']),
        ]

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        # ─── ITEMS TABLE ─────────────────────────────────────────────
        data = [['QTY', 'Description', 'Unit Cost', 'Total']]
        total_amount = 0

        for idx, item in enumerate(obj.items.all(), 1):
            item_total = item.total_cost
            total_amount += item_total
            data.append([
                f"{item.quantity_ordered} {item.item.unit.symbol}",
                item.item.name,
                f"{currency} {item.unit_cost:.2f}",
                f"{currency} {item_total:.2f}",
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

        # ─── TOTALS SECTION (Sales Tax and Shipping removed; only Subtotal and Total) ──────
        # We'll keep only Subtotal and Total, no tax, no shipping.
        totals_data = [
            ['Subtotal', f"{currency} {total_amount:.2f}"],
            ['Total', f"{currency} {total_amount:.2f}"],
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

        # ─── DELIVERY ADDRESS ────────────────────────────────────────
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Delivery Warehouse: {obj.delivery_warehouse.name}", self.styles['Normal']))
        if obj.delivery_warehouse.location:
            story.append(Paragraph(obj.delivery_warehouse.location, self.styles['Normal']))

        return story