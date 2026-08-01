# documents/services/stock_issue.py
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class StockIssueVoucherPDFService(BasePDFService):
    document_type = 'stock_issue_voucher'

    def _get_document_info(self):
        """Return voucher-specific document info (left column)."""
        obj = self.object
        return [
            Paragraph(f"Voucher #: {obj.reference or obj.pk}", self.styles['Normal']),
            Paragraph(f"Date: {obj.created_at.strftime('%d %B %Y %H:%M')}", self.styles['Normal']),
            Paragraph(f"Issued By: {obj.created_by.get_full_name()}", self.styles['Normal']),
        ]

    def _get_customer_info(self):
        """Return item info (right column)."""
        obj = self.object
        return [
            Paragraph("Item Details:", self.styles['CompanyHeading']),
            Paragraph(f"Item: {obj.item.name}", self.styles['Normal']),
            Paragraph(f"SKU: {obj.item.sku}", self.styles['Normal']),
            Paragraph(f"Quantity: {obj.quantity} {obj.item.unit.symbol}", self.styles['Normal']),
            Paragraph(f"From Warehouse: {obj.warehouse.name}", self.styles['Normal']),
        ]

    def build_body(self, story):
        obj = self.object

        # Show remaining stock
        from inventory.models import Stock
        stock = Stock.objects.filter(item=obj.item, warehouse=obj.warehouse).first()

        # ─── STOCK DETAILS ───────────────────────────────────────────
        data = [
            ['Reference', obj.reference or 'N/A'],
            ['Notes', obj.notes or 'N/A'],
            ['Remaining Stock', f"{stock.quantity} {obj.item.unit.symbol}" if stock else 'N/A'],
        ]

        table = Table(data, colWidths=[3.5*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ]))
        story.append(table)

        return story