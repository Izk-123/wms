from django.db import models
from accounts.models import User
from company_settings.numbering import generate_next_number
from operations.models import Project


class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name


class Asset(models.Model):
    CONDITION_CHOICES = (
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("poor", "Poor"),
        ("out_of_service", "Out of Service"),
    )

    STATUS_CHOICES = (
        ("available", "Available"),
        ("assigned", "Assigned"),
        ("under_maintenance", "Under Maintenance"),
        ("retired", "Retired"),
        ("lost", "Lost"),
    )

    ASSET_TYPE_CHOICES = (
        ("tool", "Tool"),
        ("equipment", "Equipment"),
        ("vehicle", "Vehicle"),
        ("it_asset", "IT Asset"),
        ("other", "Other"),
    )

    asset_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    asset_type = models.CharField(
        max_length=30,
        choices=ASSET_TYPE_CHOICES,
        default="tool"
    )
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name='assets'
    )
    brand = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True, unique=True,
                                     null=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="good"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available"
    )
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    requires_calibration = models.BooleanField(default=False)
    next_calibration_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='registered_assets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        permissions = [
            ("assign_asset", "Can assign asset"),
            ("return_asset", "Can return asset"),
            ("schedule_maintenance", "Can schedule maintenance"),
        ]

    def __str__(self):
        return f"{self.asset_number} — {self.name}"

    @property
    def is_available(self):
        return self.status == "available"

    @property
    def current_assignment(self):
        return self.assignments.filter(
            returned_at__isnull=True
        ).first()
        
    def save(self, *args, **kwargs):
        if not self.pk and not self.asset_number:
            self.asset_number = generate_next_number("ASSET_PREFIX", Asset, field="asset_number", padding=5)
        super().save(*args, **kwargs)


class AssetAssignment(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='assignments'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='asset_assignments'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='asset_assignments'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='assets_assigned_by'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(
        max_length=20,
        choices=Asset.CONDITION_CHOICES,
        blank=True
    )
    notes = models.TextField(blank=True)
    return_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.asset.name} → {self.assigned_to.get_full_name()}"

    @property
    def is_active(self):
        return self.returned_at is None


class MaintenanceRecord(models.Model):
    MAINTENANCE_TYPE_CHOICES = (
        ("preventive", "Preventive"),
        ("corrective", "Corrective"),
        ("calibration", "Calibration"),
        ("inspection", "Inspection"),
    )

    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name='maintenance_records'
    )
    maintenance_type = models.CharField(
        max_length=20,
        choices=MAINTENANCE_TYPE_CHOICES,
        default="preventive"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    performed_by = models.CharField(
        max_length=255,
        blank=True,
        help_text="Person or company who performed maintenance"
    )
    cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=0
    )
    description = models.TextField(blank=True)
    findings = models.TextField(blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='maintenance_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_date']

    def __str__(self):
        return (
            f"{self.asset.name} — "
            f"{self.get_maintenance_type_display()} "
            f"({self.scheduled_date})"
        )