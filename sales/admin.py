"""
sales/admin.py
Simplified admin configuration for Sales module.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RelatedDropdownFilter
from .models import (
    Customer, Quotation, QuotationItem,
    SalesOrder, SalesOrderItem,
    Invoice, InvoiceItem,
    Payment
)


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'email', 'phone')
    ordering = ('name',)


# ─── Quotation Admin ────────────────────────────────

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0
    fields = ('item', 'quantity', 'unit_price', 'notes')


@admin.register(Quotation)
class QuotationAdmin(ModelAdmin):
    list_display = (
        'reference', 'customer', 'quotation_date', 'valid_until',
        'status', 'total_amount', 'created_by'
    )
    list_filter = (
        'status',
        'quotation_date',
        ('customer', RelatedDropdownFilter),
    )
    search_fields = ('reference', 'customer__name', 'notes')
    readonly_fields = ('reference', 'quotation_date', 'created_by', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'customer', 'status', 'notes')
        }),
        ('Dates', {
            'fields': ('quotation_date', 'valid_until')
        }),
        ('Pricing', {
            'fields': ('discount_amount',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [QuotationItemInline]
    ordering = ('-created_at',)

    def total_amount(self, obj):
        return obj.total_amount
    total_amount.short_description = 'Total'


# ─── Sales Order Admin ──────────────────────────────

class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 0
    fields = ('item', 'quantity', 'unit_price', 'notes')


@admin.register(SalesOrder)
class SalesOrderAdmin(ModelAdmin):
    list_display = (
        'reference', 'customer', 'order_date', 'status',
        'total_amount', 'created_by'
    )
    list_filter = (
        'status',
        'order_date',
        ('customer', RelatedDropdownFilter),
    )
    search_fields = ('reference', 'customer__name', 'notes')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'customer', 'status', 'warehouse', 'notes')
        }),
        ('Pricing', {
            'fields': ('discount_amount',)
        }),
        ('Links', {
            'fields': ('quotation',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [SalesOrderItemInline]
    ordering = ('-created_at',)

    def total_amount(self, obj):
        return obj.total_amount
    total_amount.short_description = 'Total'


# ─── Invoice Admin ───────────────────────────────────

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    fields = ('item', 'quantity', 'unit_price', 'total', 'notes')
    readonly_fields = ('total',)


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = (
        'reference', 'customer', 'invoice_date', 'due_date',
        'status', 'total_amount', 'paid_amount', 'balance_due'
    )
    list_filter = (
        'status',
        'invoice_date',
        'due_date',
        ('customer', RelatedDropdownFilter),
    )
    search_fields = ('reference', 'customer__name', 'sales_order__reference')
    readonly_fields = ('reference', 'invoice_date', 'paid_amount', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'customer', 'sales_order', 'status')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date')
        }),
        ('Financials', {
            'fields': ('total_amount', 'paid_amount')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [InvoiceItemInline]
    ordering = ('-created_at',)

    def balance_due(self, obj):
        return obj.balance_due
    balance_due.short_description = 'Balance Due'


# ─── Payment Admin ──────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        'invoice', 'amount', 'payment_method', 'reference',
        'payment_date', 'received_by'
    )
    list_filter = (
        'payment_method',
        'payment_date',
        ('invoice', RelatedDropdownFilter),
    )
    search_fields = ('invoice__reference', 'reference', 'received_by__username')
    readonly_fields = ('payment_date',)
    fieldsets = (
        (None, {
            'fields': ('invoice', 'amount', 'payment_method', 'reference')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit', {
            'fields': ('received_by', 'payment_date'),
        }),
    )
    ordering = ('-payment_date',)