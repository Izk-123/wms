from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import (
    Supplier, PurchaseRequest, PurchaseRequestItem,
    PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem
)


@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    search_fields = ('name',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ModelAdmin):
    list_display = ('reference', 'supplier', 'status', 'created_by', 'created_at')
    list_filter = ('status',)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(ModelAdmin):
    list_display = ('reference', 'purchase_order', 'status', 'received_by', 'received_at')