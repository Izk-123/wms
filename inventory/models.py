from django.db import models
from accounts.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Unit(models.Model):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=10)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.symbol})"


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Item(models.Model):
    ITEM_TYPE_CHOICES = (
        ("raw_material", "Raw Material"),
        ("finished_good", "Finished Good"),
        ("consumable", "Consumable"),
        ("spare_part", "Spare Part"),
        ("equipment", "Equipment"),
    )

    sku = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='items'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='items'
    )
    item_type = models.CharField(
        max_length=50,
        choices=ITEM_TYPE_CHOICES,
        default="raw_material"
    )
    minimum_stock = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    unit_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )

    qr_code = models.ImageField(
        upload_to='qrcodes/',
        blank=True,
        null=True
    )
    barcode_image = models.ImageField(
        upload_to='barcodes/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        permissions = [
            # Custom permissions beyond the default add/change/delete/view
            ("receive_stock", "Can receive stock"),
            ("issue_stock", "Can issue stock"),
            ("transfer_stock", "Can transfer stock"),
            ("adjust_stock", "Can adjust stock"),
            ("view_stock_report", "Can view stock reports"),
        ]

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @staticmethod
    def generate_sku():
        existing = Item.objects.filter(
            sku__startswith='SKU-'
        ).values_list('sku', flat=True)

        max_num = 0
        for sku in existing:
            try:
                num = int(sku.split('-')[1])
                if num > max_num:
                    max_num = num
            except (IndexError, ValueError):
                continue

        next_num = max_num + 1
        return f"SKU-{next_num:05d}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.sku:
            self.sku = self.generate_sku()
        super().save(*args, **kwargs)


class Stock(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('item', 'warehouse')

    def __str__(self):
        return f"{self.item.name} @ {self.warehouse.name}: {self.quantity}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.item.minimum_stock


class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("TRANSFER", "Transfer"),
        ("ADJUSTMENT", "Adjustment"),
        ("RETURN", "Return"),
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name='movements'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name='movements'
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="PO number, GRN number, requisition number, etc."
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.movement_type} - {self.item.name} ({self.quantity})"