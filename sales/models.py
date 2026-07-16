"""
sales/models.py
Models for Sales module: Customer, SalesOrder, SalesOrderItem,
Invoice, InvoiceItem, Payment.
"""

from decimal import Decimal
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models import Sum
from accounts.models import User
from inventory.models import Item, Warehouse
from company_settings.numbering import generate_next_number


class Customer(models.Model):
    """Customer or client who purchases goods."""
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="Tax/VAT registration number")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SalesOrder(models.Model):
    """
    Sales Order – request from customer to purchase goods.
    Statuses: draft, pending_approval (for discount), approved, invoiced, shipped, cancelled.
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales_orders')
    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True,
                                  help_text="Warehouse from which stock will be issued.")
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_approved = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales_orders')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='approved_sales_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            # Custom permissions only – built‑in add/change/delete/view are automatic.
            ("approve_discount", "Can approve discounts on sales orders"),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("SO_PREFIX", SalesOrder, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    @property
    def total_before_discount(self):
        return sum(item.total for item in self.items.all())

    @property
    def total_amount(self):
        return self.total_before_discount - self.discount_amount

    def get_absolute_url(self):
        return reverse('sales:order-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"SO-{self.pk}"


class SalesOrderItem(models.Model):
    """Line items on a sales order."""
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    invoiced_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"


class Invoice(models.Model):
    """
    Invoice – bill sent to customer. May be generated from a Sales Order or created manually.
    Statuses: draft, sent, paid, partially_paid, cancelled.
    """
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='invoices',
                                    null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            # Custom permissions only
            ("create_invoice", "Can create invoice"),   # separate from add_invoice (automatic)
            ("cancel_invoice", "Can cancel invoice"),
            # view/change/delete are automatic
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("INVOICE_PREFIX", Invoice, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    def get_absolute_url(self):
        return reverse('sales:invoice-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"INV-{self.pk}"


class InvoiceItem(models.Model):
    """Line items on an invoice."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"


class Payment(models.Model):
    """
    Payment received from customer against an invoice.
    Supports multiple payment methods.
    """
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('airtel_money', 'Airtel Money'),
        ('mpamba', 'TNM Mpamba'),
        ('cheque', 'Cheque'),
        ('credit', 'Credit'),
    )

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True,
                                 help_text="Cheque number, transaction ID, etc.")
    payment_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments_received')
    notes = models.TextField(blank=True)

    class Meta:
        permissions = [
            # Custom permissions only
            ("receive_payment", "Can receive payment"),
            # view/delete are automatic
        ]

    def get_absolute_url(self):
        return self.invoice.get_absolute_url()

    def __str__(self):
        return f"{self.invoice.reference} - {self.amount} ({self.payment_method})"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = generate_next_number("RECEIPT_PREFIX", Payment, field="receipt_number", padding=6)
        super().save(*args, **kwargs)