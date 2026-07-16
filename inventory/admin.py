from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Category, Unit, Warehouse, Item, Stock, StockMovement


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Unit)
class UnitAdmin(ModelAdmin):
    list_display = ('name', 'symbol')
    search_fields = ('name',)


@admin.register(Warehouse)
class WarehouseAdmin(ModelAdmin):
    list_display = ('name', 'location', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(ModelAdmin):
    list_display = ('sku', 'name', 'category', 'unit', 'item_type',
                    'minimum_stock', 'unit_cost', 'is_active')
    list_filter = ('category', 'item_type', 'is_active')
    search_fields = ('sku', 'name')


@admin.register(Stock)
class StockAdmin(ModelAdmin):
    list_display = ('item', 'warehouse', 'quantity', 'last_updated')
    list_filter = ('warehouse',)
    search_fields = ('item__name', 'item__sku')


@admin.register(StockMovement)
class StockMovementAdmin(ModelAdmin):
    list_display = ('item', 'movement_type', 'quantity',
                    'warehouse', 'reference', 'created_by', 'created_at')
    list_filter = ('movement_type', 'warehouse')
    search_fields = ('item__name', 'reference')
    readonly_fields = ('created_at',)