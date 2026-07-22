"""
finance/models.py
Models for Finance module: Account (Chart of Accounts),
JournalEntry, JournalLine, Expense, CashDrawer, CashTransaction,
SupplierBill, FinanceAuditLog.
"""

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.urls import reverse
from accounts.models import User
from company_settings.numbering import generate_next_number
from company_settings.services import get_setting
from sales.models import Payment  # for choices in Expense


class Account(models.Model):
    """
    Chart of Accounts – each account has a type and can have a parent for hierarchy.
    """
    ACCOUNT_TYPES = (
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('income', 'Income'),
        ('expense', 'Expense'),
    )

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='children')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    """
    Journal Entry – the core accounting record. Contains multiple JournalLine entries.
    Each entry must balance (total debit = total credit) – enforced in the creation logic.
    """
    entry_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=50, blank=True,
                                 help_text="Reference to source document (invoice, PO, etc.)")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    is_reconciled = models.BooleanField(default=False)

    class Meta:
        permissions = [
            ("approve_journalentry", "Can approve journal entries"),
        ]

    @property
    def total_debit(self):
        return self.lines.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

    @property
    def total_credit(self):
        return self.lines.aggregate(total=Sum('credit'))['total'] or Decimal('0.00')

    def __str__(self):
        return f"{self.entry_date} - {self.description}"
    
    def save(self, *args, **kwargs):
        if not self.reference and get_setting("AUTO_JOURNAL_REFERENCE", True):
            self.reference = generate_next_number("JOURNAL_PREFIX", JournalEntry, padding=6)
        super().save(*args, **kwargs)


class JournalLine(models.Model):
    """
    Individual line within a journal entry: one account and a debit or credit amount.
    """
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)

    def clean(self):
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("Either debit or credit must be > 0.")
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("Cannot have both debit and credit on the same line.")

    def __str__(self):
        return f"{self.account.name} - Debit: {self.debit} Credit: {self.credit}"


class Expense(models.Model):
    """
    Expense – records money spent by the company.
    Requires approval (by Finance Manager or higher) and payment.
    """
    EXPENSE_CATEGORY_CHOICES = (
        ('fuel', 'Fuel'),
        ('wages', 'Wages'),
        ('building_materials', 'Building Materials'),
        ('transport', 'Transport'),
        ('office', 'Office Expenses'),
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    )

    # ─── Fixed: allow null so first save doesn't violate UNIQUE ───
    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    category = models.CharField(max_length=30, choices=EXPENSE_CATEGORY_CHOICES, default='other')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_expenses')
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='paid_expenses')
    payment_method = models.CharField(
        max_length=20,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        blank=True,
        help_text="Method used to pay this expense."
    )
    # In Expense model, add:
    department = models.ForeignKey('hr.Department', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("approve_expense", "Can approve expense"),
            ("pay_expense", "Can pay expense"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            # First save with no reference (will be NULL)
            super().save(*args, **kwargs)
            # Now generate reference from the primary key
            self.reference = f"EXP-{self.pk:06d}"
            # Update only the reference field
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('finance:expense-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"EXP-{self.pk}"


# ─── Cashier / Cash Management ───────────────────────────

class CashDrawer(models.Model):
    """
    Represents a physical cash drawer session for a cashier.
    One cashier can only have one OPEN drawer at a time.
    """
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
    )

    cashier = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_drawers')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    expected_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True)

    class Meta:
        permissions = [
            ("manage_cash_drawer", "Can open/close cash drawer"),
            ("receive_cash", "Can receive cash payments"),
            ("pay_cash", "Can make cash payments"),
        ]
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.cashier.username} – {self.opened_at:%d/%m/%Y %H:%M}"

    @property
    def is_open(self):
        return self.status == 'open'


class CashTransaction(models.Model):
    """
    Every cash movement (in/out) against an open drawer.
    """
    TRANSACTION_TYPES = (
        ('payment_in', 'Customer Payment'),
        ('payment_out', 'Supplier Payment'),
        ('expense', 'Expense'),
        ('transfer', 'Transfer'),
        ('refund', 'Refund'),
    )

    drawer = models.ForeignKey(CashDrawer, on_delete=models.PROTECT, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, blank=True)  # e.g. invoice/expense reference
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_transactions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_inflow(self):
        return self.transaction_type == 'payment_in'

    def __str__(self):
        return f"{self.get_transaction_type_display()} – {self.amount}"


# ─── Accounts Payable ─────────────────────────────────────

class SupplierBill(models.Model):
    """
    A bill received from a supplier, to be approved and paid.
    Mirrors the Expense approval/payment lifecycle so it plugs into the
    same company_settings approval matrix.
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    )

    supplier = models.ForeignKey('procurement.Supplier', on_delete=models.PROTECT, related_name='bills')
    purchase_order = models.ForeignKey('procurement.PurchaseOrder', on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='bills')
    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    bill_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_supplier_bills')
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='paid_supplier_bills')
    payment_method = models.CharField(
        max_length=20,
        choices=Payment.PAYMENT_METHOD_CHOICES,
        blank=True,
        help_text="Method used to pay this bill."
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='supplier_bills')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("approve_supplierbill", "Can approve supplier bill"),
            ("pay_supplierbill", "Can pay supplier bill"),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = f"BILL-{self.pk:06d}"
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.amount - self.paid_amount

    def get_absolute_url(self):
        return reverse('finance:supplier-bill-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"BILL-{self.pk}"


# ─── Audit Trail ──────────────────────────────────────────

class FinanceAuditLog(models.Model):
    """
    Records who did what to which finance record, and the before/after state.
    Written by finance.services.log_finance_audit() — do not edit directly.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='finance_audit_entries')
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField()
    reference = models.CharField(max_length=50, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        return f"{self.user.username} – {self.action} – {self.created_at:%Y-%m-%d %H:%M}"
    
# ─── Bank Accounts & Reconciliation ────────────────────────────────

class BankAccount(models.Model):
    """
    Bank account linked to a specific Account (Chart of Accounts).
    """
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name='bank_account')
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    branch = models.CharField(max_length=100, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    swift = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bank_name} – {self.account_number}"


class BankTransaction(models.Model):
    """
    System‑generated transactions (from sales, payments, expenses, etc.)
    that appear on a bank statement.
    """
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='transactions')
    date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # positive = credit, negative = debit
    reconciled = models.BooleanField(default=False)
    source = models.CharField(max_length=50, blank=True)  # e.g., 'payment', 'expense'
    source_id = models.PositiveIntegerField(null=True, blank=True)  # ID of related document

    def __str__(self):
        return f"{self.date} – {self.description} – {self.amount}"


class BankStatement(models.Model):
    """
    Uploaded or manually entered bank statement lines.
    """
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='statements')
    statement_date = models.DateField()
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reconciled = models.BooleanField(default=False)
    reconciliation_date = models.DateTimeField(null=True, blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    matched_transaction = models.ForeignKey(BankTransaction, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.account.account_number} – {self.statement_date} – {self.amount}"


class Reconciliation(models.Model):
    """
    A reconciliation session for a bank account.
    """
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='reconciliations')
    statement_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=15, decimal_places=2)
    total_debits = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credits = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    difference = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('completed', 'Completed')], default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.account} – {self.statement_date}"

    def calculate_totals(self):
        """Re‑calculate total debits/credits from matched statements."""
        self.total_credits = self.account.statements.filter(
            reconciled=True, statement_date__lte=self.statement_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.total_debits = self.account.transactions.filter(
            reconciled=True, date__lte=self.statement_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        self.difference = (self.opening_balance + self.total_credits - self.total_debits) - self.closing_balance
        self.save()


# ─── Budgets ────────────────────────────────────────────────────────

class Budget(models.Model):
    """
    A budget for a specific department and fiscal year.
    """
    department = models.ForeignKey('hr.Department', on_delete=models.PROTECT, related_name='budgets', null=True, blank=True)
    fiscal_year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fiscal_year', 'department']
        unique_together = ['department', 'fiscal_year']

    def __str__(self):
        return f"{self.department.name if self.department else 'General'} – {self.fiscal_year}"


class BudgetLine(models.Model):
    """
    Line item for a budget, e.g., expense category.
    """
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lines')
    category = models.CharField(max_length=50, choices=Expense.EXPENSE_CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.budget} – {self.get_category_display()}"


# ─── Fiscal Periods ────────────────────────────────────────────────

class FiscalPeriod(models.Model):
    """
    Represents a fiscal month or year.
    """
    name = models.CharField(max_length=50, unique=True)  # e.g., "January 2025"
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name