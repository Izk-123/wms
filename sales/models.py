"""
sales/models.py
Simplified Sales module with Order-to-Cash workflow.
"""

from decimal import Decimal
from django.db import models
from django.urls import reverse
from accounts.models import User
from inventory.models import Item, Warehouse


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Quotation(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='quotations')
    quotation_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quotations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store PDF
    pdf_file = models.FileField(upload_to='pdfs/quotations/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = f"QT-{self.pk:06d}"
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
        return reverse('sales:quotation-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.reference or f"QT-{self.pk}"


class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return self.quantity * self.unit_price


class SalesOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales_orders')
    order_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    # Link back to quotation
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_orders'
    )

    # Store PDF
    pdf_file = models.FileField(upload_to='pdfs/sales_orders/', blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = f"SO-{self.pk:06d}"
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
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return self.quantity * self.unit_price


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('cancelled', 'Cancelled'),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    # Store PDF
    pdf_file = models.FileField(upload_to='pdfs/invoices/', blank=True, null=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = f"INV-{self.pk:06d}"
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount

    def get_absolute_url(self):
        return reverse('sales:invoice-detail', kwargs={'pk': self.pk})


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('BANK', 'Bank Transfer'),
        ('AIRTE', 'Airtel Money'),
        ('MPAMB', 'TNM Mpamba'),
        ('CHEQUE', 'Cheque'),
    )

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payments_received')
    notes = models.TextField(blank=True)

    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)

    # Store receipt PDF
    receipt_pdf = models.FileField(upload_to='pdfs/receipts/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            super().save(*args, **kwargs)
            self.receipt_number = f"REC-{self.pk:06d}"
            super().save(update_fields=['receipt_number'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.reference} - {self.amount}"