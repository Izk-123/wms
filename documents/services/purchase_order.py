# documents/services/purchase_order.py

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class PurchaseOrderPDFService(BasePDFService):
    document_type = 'purchase_order'

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        story.append(Paragraph("PURCHASE ORDER", self.styles['CompanyHeading']))
        story.append(Paragraph(f"PO Number: {obj.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Date: {obj.created_at.strftime('%d %B %Y')}", self.styles['Normal']))
        story.append(Paragraph(f"Expected Delivery: {obj.expected_delivery.strftime('%d %B %Y') if obj.expected_delivery else 'TBD'}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # Supplier
        story.append(Paragraph("Supplier:", self.styles['CompanyHeading']))
        story.append(Paragraph(obj.supplier.name, self.styles['Normal']))
        if obj.supplier.address:
            story.append(Paragraph(obj.supplier.address, self.styles['Normal']))
        story.append(Spacer(1, 0.5*cm))

        # Items
        data = [['#', 'Item', 'Qty', 'Unit Cost', 'Total']]
        for idx, item in enumerate(obj.items.all(), 1):
            data.append([
                str(idx),
                item.item.name,
                f"{item.quantity_ordered} {item.item.unit.symbol}",
                f"{item.unit_cost:.2f}",
                f"{item.total_cost:.2f}",
            ])
        data.append(['', '', '', 'Total', f"{obj.total_value:.2f}"])

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

        # Delivery address
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Delivery Warehouse: {obj.delivery_warehouse.name}", self.styles['Normal']))
        if obj.delivery_warehouse.location:
            story.append(Paragraph(obj.delivery_warehouse.location, self.styles['Normal']))

        return story