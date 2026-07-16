from decimal import Decimal
from django.db import transaction
from .models import Account, JournalEntry, JournalLine
from sales.models import Payment

def create_sales_payment_journal_entry(payment):
    """Debit payment method account, credit Sales Revenue."""
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            description=f"Payment for invoice {payment.invoice.reference}",
            reference=payment.invoice.reference,
            created_by=payment.received_by,
        )
        method_map = {
            'cash': '1000',
            'bank': '1010',
            'airtel_money': '1020',
            'mpamba': '1030',
            'cheque': '1040',
        }
        debit_account = Account.objects.get(code=method_map.get(payment.payment_method, '1000'))
        JournalLine.objects.create(entry=entry, account=debit_account, debit=payment.amount)
        sales_account = Account.objects.get(code='4000')
        JournalLine.objects.create(entry=entry, account=sales_account, credit=payment.amount)

def create_expense_journal_entry(expense):
    """Debit expense account, credit Cash (or Accounts Payable)."""
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            description=f"Expense {expense.reference} - {expense.category}",
            reference=expense.reference,
            created_by=expense.approved_by or expense.created_by,
        )
        # Debit expense account (e.g., 6000)
        expense_account = Account.objects.get(code='6000')
        JournalLine.objects.create(entry=entry, account=expense_account, debit=expense.amount)
        # Credit cash account (or accounts payable if not paid immediately)
        cash_account = Account.objects.get(code='1000')
        JournalLine.objects.create(entry=entry, account=cash_account, credit=expense.amount)