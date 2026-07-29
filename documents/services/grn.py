# documents/services/grn.py

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class GoodsReceiptPDFService(BasePDFService):
    document_type = 'goods_receipt'

    def build_body(self, story):
        obj = self.object
        po = obj.purchase_order
        currency = self.company_data['currency']

        story.append(Paragraph("GOODS RECEIPT NOTE", self.styles['CompanyHeading']))
        story.append(Paragraph(f"GRN Number: {obj.reference}", self.styles['Normal']))
        story.append(Paragraph(f"PO Reference: {po.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Supplier: {po.supplier.name}", self.styles['Normal']))
        story.append(Paragraph(f"Received Date: {obj.received_at.strftime('%d %B %Y %H:%M')}", self.styles['Normal']))
        story.append(Paragraph(f"Received By: {obj.received_by.get_full_name()}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # Items
        data = [['#', 'Item', 'Qty Received', 'Unit', 'Notes']]
        for idx, item in enumerate(obj.items.all(), 1):
            data.append([
                str(idx),
                item.purchase_order_item.item.name,
                f"{item.quantity_received}",
                item.purchase_order_item.item.unit.symbol,
                item.notes or '',
            ])
        if len(data) == 1:
            data.append(['', 'No items', '', '', ''])

        col_widths = [1*cm, 6*cm, 3*cm, 2*cm, 4*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (1,1), (-1,-1), 'LEFT'),
            ('ALIGN', (2,1), (-1,-1), 'CENTER'),
        ]))
        story.append(table)

        # Warehouse
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Warehouse: {po.delivery_warehouse.name}", self.styles['Normal']))

        return story