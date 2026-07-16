from django.db import models
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError

from accounts.models import Role

class Company(models.Model):
    """Single company record – only one instance should exist."""
    name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="TPIN / VAT")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    physical_address = models.TextField(blank=True)
    postal_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Malawi")
    timezone = models.CharField(max_length=50, default="Africa/Blantyre")
    currency = models.CharField(max_length=10, default="MWK")
    currency_symbol = models.CharField(max_length=10, default="MK")
    logo = models.ImageField(upload_to="company/", blank=True, null=True)
    favicon = models.ImageField(upload_to="company/", blank=True, null=True)

    class Meta:
        verbose_name_plural = "Company Profile"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Enforce only one record
        if not self.pk and Company.objects.exists():
            raise ValidationError("A company profile already exists.")
        super().save(*args, **kwargs)


class SystemSetting(models.Model):
    """Key-value store for all other settings."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_boolean = models.BooleanField(default=False)

    def __str__(self):
        return self.key

    @property
    def typed_value(self):
        if self.is_boolean:
            return self.value.lower() in ("true", "1", "yes", "on")
        return self.value


class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    """Available payment methods (Cash, Bank, Airtel Money, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)  # e.g. CASH, BANK, AIRTEL
    is_active = models.BooleanField(default=True)
    requires_reference = models.BooleanField(default=False)  # e.g. cheque number, transaction ID
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
    

class ApprovalRule(models.Model):
    """
    Defines who can approve a specific transaction type based on amount.
    """
    ACTION_CHOICES = (
        ('sales_discount', 'Sales Discount'),
        ('purchase_request', 'Purchase Request'),
        ('purchase_order', 'Purchase Order'),
        ('expense', 'Expense'),
        ('journal_entry', 'Journal Entry'),
        ('material_request', 'Material Request'),
        ('supplier_payment', 'Supplier Payment'),
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    min_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    required_role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='company_approval_rules')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower order = higher priority")

    class Meta:
        ordering = ['action', 'order', 'min_amount']
        unique_together = ['action', 'min_amount', 'max_amount']

    def __str__(self):
        max_display = f"– {self.max_amount}" if self.max_amount else "+"
        return f"{self.action} {self.min_amount} {max_display} → {self.required_role.name}"

class ApprovalRequest(models.Model):
    """
    Tracks pending approval requests with status and history.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    action = models.CharField(max_length=50, choices=ApprovalRule.ACTION_CHOICES)
    reference = models.CharField(max_length=100, blank=True, help_text="Reference number of the document")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    requested_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name='company_approval_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='company_approved_requests')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    # Generic relation to the original document (optional)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} – {self.reference} ({self.status})"

    @property
    def is_pending(self):
        return self.status == 'pending'