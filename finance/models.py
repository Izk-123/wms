"""
finance/models.py
Models for Finance module: Account (Chart of Accounts),
JournalEntry, JournalLine, Expense.
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
            # Custom permissions
            ("approve_journalentry", "Can approve journal entries"),
            # add/view are automatic
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
        # Journal entries may be manual or auto-generated
        # Only generate if reference is blank AND we want auto-numbering
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

    reference = models.CharField(max_length=50, unique=True, blank=True)
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
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            # Custom permissions
            ("approve_expense", "Can approve expense"),
            ("pay_expense", "Can pay expense"),
            # add/view are automatic
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("EXPENSE_PREFIX", Expense, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('finance:expense-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"EXP-{self.pk}"