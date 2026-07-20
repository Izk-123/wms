"""
finance/admin.py
Admin configuration for:
- Account (Chart of Accounts)
- JournalEntry & JournalLine (audit trail)
- Expense
All use Unfold's ModelAdmin.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import (
    RelatedDropdownFilter,
)
from .models import Account, JournalEntry, JournalLine, Expense


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'parent', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('code',)
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'account_type')
        }),
        ('Hierarchy', {
            'fields': ('parent',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    fields = ('account', 'debit', 'credit', 'description')
    readonly_fields = ('debit', 'credit')  # prevent manual edits via admin; use views for manual entries


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    list_display = (
        'entry_date', 'description', 'reference', 'created_by',
        'total_debit', 'total_credit', 'is_reconciled'
    )
    list_filter = (
        'entry_date',
        'is_reconciled',
        ('created_by', RelatedDropdownFilter),
    )
    search_fields = ('description', 'reference', 'created_by__username')
    readonly_fields = ('entry_date', 'created_at', 'created_by')
    fieldsets = (
        (None, {
            'fields': ('entry_date', 'description', 'reference', 'is_reconciled')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [JournalLineInline]
    ordering = ('-entry_date',)

    def total_debit(self, obj):
        return obj.total_debit
    total_debit.short_description = 'Total Debit'

    def total_credit(self, obj):
        return obj.total_credit
    total_credit.short_description = 'Total Credit'

@admin.action(description='Approve selected expenses')
def approve_expenses(modeladmin, request, queryset):
    for expense in queryset:
        expense.status = 'approved'
        expense.save()

@admin.register(Expense)
class ExpenseAdmin(ModelAdmin):
    list_display = (
        'reference', 'category', 'amount', 'expense_date',
        'status', 'created_by', 'approved_by', 'paid_by'
    )
    list_filter = (
        'category',
        'status',
        'expense_date',
        ('created_by', RelatedDropdownFilter),
        ('approved_by', RelatedDropdownFilter),
    )
    search_fields = ('reference', 'description', 'notes')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'category', 'amount', 'description')
        }),
        ('Status', {
            'fields': ('status', 'approved_by', 'paid_by', 'payment_method')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    ordering = ('-created_at',)
    actions = [approve_expenses]