from django.db import models
from accounts.models import User
from company_settings.numbering import generate_next_number
from inventory.models import Item, Warehouse


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class PurchaseRequest(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("ordered", "Ordered"),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchase_requests'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("approve_purchaserequest", "Can approve purchase request"),
            ("reject_purchaserequest", "Can reject purchase request"),
        ]

    def __str__(self):
        return self.reference or f"PR-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("PR_PREFIX", PurchaseRequest, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)


class PurchaseRequestItem(models.Model):
    request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT
    )
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_unit_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} x {self.quantity}"

    @property
    def estimated_total(self):
        return self.quantity * self.estimated_unit_cost


class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("sent", "Sent to Supplier"),
        ("partial", "Partially Received"),
        ("received", "Fully Received"),
        ("cancelled", "Cancelled"),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='purchase_orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    delivery_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT
    )
    expected_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchase_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference or f"PO-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("PO_PREFIX", PurchaseOrder, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)

    @property
    def total_value(self):
        return sum(i.total_cost for i in self.items.all())


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT
    )
    quantity_ordered = models.DecimalField(max_digits=15, decimal_places=2)
    quantity_received = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} x {self.quantity_ordered}"

    @property
    def total_cost(self):
        return self.quantity_ordered * self.unit_cost

    @property
    def quantity_pending(self):
        return self.quantity_ordered - self.quantity_received


class GoodsReceipt(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name='goods_receipts'
    )
    received_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='goods_receipts'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    notes = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return self.reference or f"GRN-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("GRN_PREFIX", GoodsReceipt, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)


class GoodsReceiptItem(models.Model):
    receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name='items'
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT
    )
    quantity_received = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.purchase_order_item.item.name} x {self.quantity_received}"