# documents/services/grn.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class GoodsReceiptPDFService(BasePDFService):
    document_type = 'goods_receipt'

    def _get_document_info(self):
        obj = self.object
        po = obj.purchase_order
        return [
            Paragraph(f"GRN #: {obj.reference}", self.styles['Normal']),
            Paragraph(f"PO Reference: {po.reference}", self.styles['Normal']),
            Paragraph(f"Received Date: {obj.received_at.strftime('%d %B %Y %H:%M')}", self.styles['Normal']),
        ]

    def _get_customer_info(self):
        obj = self.object
        po = obj.purchase_order
        return [
            Paragraph("Supplier:", self.styles['CompanyHeading']),
            Paragraph(po.supplier.name, self.styles['Normal']),
            Paragraph(po.supplier.address or '', self.styles['Normal']),
            Paragraph(f"Received By: {obj.received_by.get_full_name()}", self.styles['Normal']),
        ]

    def build_body(self, story):
        obj = self.object
        po = obj.purchase_order

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

        data = [['QTY', 'Description', 'Unit', 'Notes']]
        for item in obj.items.all():
            data.append([
                f"{item.quantity_received}",
                item.purchase_order_item.item.name,
                item.purchase_order_item.item.unit.symbol,
                item.notes or '',
            ])
        if len(data) == 1:
            data.append(['', 'No items', '', ''])

        col_widths = [2.5*cm, 7*cm, 2.5*cm, 4.5*cm]
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
            ('ALIGN', (2,1), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(table)

        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Warehouse: {po.delivery_warehouse.name}", self.styles['Normal']))
        if po.delivery_warehouse.location:
            story.append(Paragraph(po.delivery_warehouse.location, self.styles['Normal']))

        return story