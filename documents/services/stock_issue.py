# documents/services/stock_issue.py

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from .base import BasePDFService

class StockIssueVoucherPDFService(BasePDFService):
    document_type = 'stock_issue_voucher'

    def build_body(self, story):
        obj = self.object
        currency = self.company_data['currency']

        story.append(Paragraph("STOCK ISSUE VOUCHER", self.styles['CompanyHeading']))
        story.append(Paragraph(f"Voucher #: {obj.reference or obj.pk}", self.styles['Normal']))
        story.append(Paragraph(f"Date: {obj.created_at.strftime('%d %B %Y %H:%M')}", self.styles['Normal']))
        story.append(Paragraph(f"Issued By: {obj.created_by.get_full_name()}", self.styles['Normal']))
        story.append(Paragraph(f"Item: {obj.item.name}", self.styles['Normal']))
        story.append(Paragraph(f"SKU: {obj.item.sku}", self.styles['Normal']))
        story.append(Paragraph(f"Quantity: {obj.quantity} {obj.item.unit.symbol}", self.styles['Normal']))
        story.append(Paragraph(f"From Warehouse: {obj.warehouse.name}", self.styles['Normal']))
        if obj.reference:
            story.append(Paragraph(f"Reference: {obj.reference}", self.styles['Normal']))
        if obj.notes:
            story.append(Paragraph(f"Notes: {obj.notes}", self.styles['Normal']))

        # Optional: show remaining stock
        from inventory.models import Stock
        stock = Stock.objects.filter(item=obj.item, warehouse=obj.warehouse).first()
        if stock:
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(f"Remaining Stock: {stock.quantity} {obj.item.unit.symbol}", self.styles['Normal']))

        return story