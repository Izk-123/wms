from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Asset, AssetCategory, AssetAssignment, MaintenanceRecord


@admin.register(AssetCategory)
class AssetCategoryAdmin(ModelAdmin):
    list_display = ('name',)


@admin.register(Asset)
class AssetAdmin(ModelAdmin):
    list_display = (
        'asset_number', 'name', 'asset_type',
        'status', 'condition', 'location'
    )
    list_filter = ('status', 'asset_type', 'condition')
    search_fields = ('asset_number', 'name', 'serial_number')


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(ModelAdmin):
    list_display = (
        'asset', 'assigned_to', 'project',
        'assigned_at', 'returned_at'
    )


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(ModelAdmin):
    list_display = (
        'asset', 'maintenance_type', 'status',
        'scheduled_date', 'completed_date'
    )