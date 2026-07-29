# documents/services/receipt.py
from .base import BasePDFService
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

class ReceiptPDFService(BasePDFService):
    document_type = 'receipt'

    def build_body(self, story):
        payment = self.object
        invoice = payment.invoice
        currency = self.company_data['currency']

        # Get receiver name – fallback to username if full name is empty
        receiver = payment.received_by.get_full_name() or payment.received_by.username

        story.append(Paragraph("RECEIPT", self.styles['CompanyHeading']))
        story.append(Paragraph(f"Receipt No: {payment.receipt_number}", self.styles['Normal']))
        story.append(Paragraph(f"Invoice: {invoice.reference}", self.styles['Normal']))
        story.append(Paragraph(f"Customer: {invoice.customer.name}", self.styles['Normal']))
        story.append(Paragraph(f"Payment Date: {payment.payment_date.strftime('%d %B %Y %H:%M')}", self.styles['Normal']))
        story.append(Paragraph(f"Amount Paid: {currency} {payment.amount:.2f}", self.styles['Normal']))
        story.append(Paragraph(f"Payment Method: {payment.get_payment_method_display()}", self.styles['Normal']))
        story.append(Paragraph(f"Received By: {receiver}", self.styles['Normal']))

        # Remaining balance
        balance = invoice.balance_due
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"Balance Due: {currency} {balance:.2f}", self.styles['Normal']))
        return story