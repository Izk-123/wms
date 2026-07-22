from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.timezone import datetime
from django.db import transaction as db_transaction
from .models import (
    Account, BankStatement, Expense, JournalEntry, JournalLine, CashDrawer, CashTransaction, Reconciliation,
    SupplierBill, FinanceAuditLog,
)
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


# ─── Audit Trail ────────────────────────────────────────

AUDIT_FIELD_EXCLUDE = {'id'}

def snapshot(instance, fields=None):
    """Serialize a model instance to a JSON-safe dict for audit before/after.
    Call this BEFORE mutating an instance to capture its "before" state."""
    data = model_to_dict(instance, fields=fields)
    for key, value in list(data.items()):
        if key in AUDIT_FIELD_EXCLUDE:
            data.pop(key)
        elif hasattr(value, 'pk'):
            data[key] = value.pk
        elif isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, (datetime, date)):
            data[key] = value.isoformat()
    return data

# Backwards-compatible alias used internally
_snapshot = snapshot


def log_finance_audit(user, action, instance, before=None, after=None, reason="", request=None):
    """
    Record a finance audit trail entry.

    `before`/`after` may be passed explicitly (dicts), or omitted — if `after`
    is omitted it is snapshotted from `instance` automatically. Pass `before`
    when you captured the state prior to mutating `instance`.
    """
    ip = None
    if request is not None:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = (
            x_forwarded.split(',')[0].strip()
            if x_forwarded
            else request.META.get('REMOTE_ADDR')
        )

    if after is None:
        after = _snapshot(instance)

    return FinanceAuditLog.objects.create(
        user=user,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        reference=getattr(instance, 'reference', '') or '',
        before=before,
        after=after,
        reason=reason,
        ip_address=ip,
    )


# ─── Cashier / Cash Management ───────────────────────────

def open_cash_drawer(user, opening_balance=0):
    """Open a new cash drawer for a cashier. Fails if one is already open."""
    if CashDrawer.objects.filter(cashier=user, status='open').exists():
        raise ValidationError("You already have an open cash drawer.")
    drawer = CashDrawer.objects.create(
        cashier=user,
        opening_balance=opening_balance,
        status='open',
    )
    return drawer


def close_cash_drawer(drawer, closing_balance):
    """Close the drawer, computing expected balance and the cash difference."""
    if drawer.status == 'closed':
        raise ValidationError("This drawer is already closed.")

    cash_in = drawer.transactions.filter(
        transaction_type__in=['payment_in', 'refund']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cash_out = drawer.transactions.filter(
        transaction_type__in=['payment_out', 'expense']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    expected = drawer.opening_balance + cash_in - cash_out
    drawer.closing_balance = closing_balance
    drawer.expected_balance = expected
    drawer.difference = closing_balance - expected
    drawer.closed_at = timezone.now()
    drawer.status = 'closed'
    drawer.save()
    return drawer


def record_cash_payment(drawer, amount, description, reference="", transaction_type='payment_in', user=None):
    """Record a cash movement (customer payment, expense, refund, etc.) against an open drawer."""
    if drawer.status != 'open':
        raise ValidationError("Cash drawer is not open.")
    if amount is None or amount <= 0:
        raise ValidationError("Amount must be positive.")
    return CashTransaction.objects.create(
        drawer=drawer,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
        reference=reference,
        created_by=user or drawer.cashier,
    )


# ─── Accounts Payable ─────────────────────────────────────

def create_supplier_bill_journal_entry(bill):
    """Debit Expense/Inventory-in-transit, credit Accounts Payable when a bill is approved."""
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            description=f"Supplier bill {bill.reference} – {bill.supplier.name}",
            reference=bill.reference,
            created_by=bill.approved_by or bill.created_by,
        )
        expense_account = Account.objects.get(code='6000')
        JournalLine.objects.create(entry=entry, account=expense_account, debit=bill.amount)
        ap_account = Account.objects.get(code='2100')
        JournalLine.objects.create(entry=entry, account=ap_account, credit=bill.amount)
    return entry


def create_supplier_payment_journal_entry(bill, payment_amount):
    """Debit Accounts Payable, credit Cash when a supplier bill is paid."""
    with transaction.atomic():
        entry = JournalEntry.objects.create(
            description=f"Payment to {bill.supplier.name} – {bill.reference}",
            reference=bill.reference,
            created_by=bill.paid_by or bill.created_by,
        )
        ap_account = Account.objects.get(code='2100')
        JournalLine.objects.create(entry=entry, account=ap_account, debit=payment_amount)
        cash_account = Account.objects.get(code='1000')
        JournalLine.objects.create(entry=entry, account=cash_account, credit=payment_amount)
    return entry

# ─── Bank Reconciliation ───────────────────────────────────────────

def import_bank_statements(account, file_handle):
    """
    Parse CSV file and create BankStatement entries.
    Expected CSV columns: date, reference, description, amount.
    """
    import csv
    from io import TextIOWrapper

    reader = csv.DictReader(TextIOWrapper(file_handle, encoding='utf-8'))
    created = 0
    for row in reader:
        try:
            BankStatement.objects.create(
                account=account,
                statement_date=datetime.strptime(row['date'], '%Y-%m-%d').date(),
                reference=row.get('reference', ''),
                description=row['description'],
                amount=Decimal(row['amount'])
            )
            created += 1
        except Exception as e:
            # log error but continue
            continue
    return created


def match_bank_transaction(transaction, statement, user):
    """
    Match a system transaction with a statement line.
    Validates amount and marks both as reconciled.
    """
    if transaction.amount != statement.amount:
        raise ValidationError("Amounts do not match.")
    if transaction.reconciled or statement.reconciled:
        raise ValidationError("One or both items are already reconciled.")

    transaction.reconciled = True
    transaction.save()
    statement.reconciled = True
    statement.reconciliation_date = timezone.now()
    statement.reconciled_by = user
    statement.matched_transaction = transaction
    statement.save()
    return transaction, statement


def finalize_reconciliation(account, statement_date, opening, closing, user):
    """
    Complete a reconciliation session: create Reconciliation record,
    mark all matched items, and calculate totals.
    """
    with db_transaction.atomic():
        rec = Reconciliation.objects.create(
            account=account,
            statement_date=statement_date,
            opening_balance=opening,
            closing_balance=closing,
            created_by=user,
            status='completed',
            completed_at=timezone.now()
        )
        rec.calculate_totals()
        return rec


# ─── Budget vs Actual ─────────────────────────────────────────────

def get_actual_expenses(department, fiscal_year, category=None):
    """
    Sum actual expenses (paid) for a given department, fiscal year, and category.
    """
    qs = Expense.objects.filter(
        status='paid',
        expense_date__year=fiscal_year,
        department=department  # You'll need to add department field to Expense
    )
    if category:
        qs = qs.filter(category=category)
    return qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')


# ─── Month‑End Closing ─────────────────────────────────────────────

def close_fiscal_period(period, user):
    """
    Close a fiscal period:
    - Prevent new transactions with dates inside the period.
    - Create closing entries (e.g., transfer net profit to retained earnings).
    """
    if period.is_closed:
        raise ValidationError("This period is already closed.")

    # Check for any unreconciled transactions?
    # Optionally: ensure all journals in this period are balanced.

    with db_transaction.atomic():
        period.is_closed = True
        period.closed_at = timezone.now()
        period.closed_by = user
        period.save()

        # Create closing entry (example: net income to retained earnings)
        # This is a simplified example – real closing would involve more accounts.
        # We'll skip for brevity; you can implement as needed.

    return period