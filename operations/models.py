from django.db import models
from accounts.models import User
from company_settings.numbering import generate_next_number
from inventory.models import Item, Warehouse


class Project(models.Model):
    STATUS_CHOICES = (
        ("planning", "Planning"),
        ("active", "Active"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    PROJECT_TYPE_CHOICES = (
        ("construction", "Construction"),
        ("manufacturing", "Manufacturing"),
        ("maintenance", "Maintenance"),
        ("other", "Other"),
    )

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project_type = models.CharField(
        max_length=30,
        choices=PROJECT_TYPE_CHOICES,
        default="construction"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planning"
    )
    site_location = models.CharField(max_length=255, blank=True)
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_projects'
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_projects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def total_material_cost(self):
        return sum(
            i.quantity * i.item.unit_cost
            for req in self.material_requests.filter(status="issued")
            for i in req.items.all()
        )


class MaterialRequest(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("issued", "Issued"),
        ("partially_issued", "Partially Issued"),
    )

    reference = models.CharField(max_length=50, unique=True, blank=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name='material_requests',
        null=True, blank=True
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='material_requests'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        help_text="Warehouse to issue materials from"
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
        related_name='approved_material_requests'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("approve_materialrequest", "Can approve material request"),
            ("issue_materialrequest", "Can issue materials from request"),
        ]

    def __str__(self):
        return self.reference or f"MR-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("MR_PREFIX", MaterialRequest, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)


class MaterialRequestItem(models.Model):
    request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT
    )
    quantity_requested = models.DecimalField(
        max_digits=15, decimal_places=2
    )
    quantity_issued = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} x {self.quantity_requested}"

    @property
    def quantity_pending(self):
        return self.quantity_requested - self.quantity_issued

    @property
    def is_fully_issued(self):
        return self.quantity_issued >= self.quantity_requested


class MaterialReturn(models.Model):
    reference = models.CharField(max_length=50, unique=True, blank=True)
    material_request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.PROTECT,
        related_name='returns'
    )
    returned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='material_returns'
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.reference or f"RTN-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.reference:
            super().save(*args, **kwargs)
            self.reference = generate_next_number("RETURN_PREFIX", MaterialReturn, padding=6)
            super().save(update_fields=['reference'])
        else:
            super().save(*args, **kwargs)


class MaterialReturnItem(models.Model):
    material_return = models.ForeignKey(
        MaterialReturn,
        on_delete=models.CASCADE,
        related_name='items'
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT
    )
    quantity_returned = models.DecimalField(
        max_digits=15, decimal_places=2
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.item.name} x {self.quantity_returned}"