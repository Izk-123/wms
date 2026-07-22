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
from .models import (
    Account, BankAccount, BankStatement, BankTransaction, Budget, BudgetLine, FiscalPeriod, JournalEntry, JournalLine, Expense,
    CashDrawer, CashTransaction, Reconciliation, SupplierBill, FinanceAuditLog,
)


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


class CashTransactionInline(admin.TabularInline):
    model = CashTransaction
    extra = 0
    fields = ('transaction_type', 'amount', 'description', 'reference', 'created_by', 'created_at')
    readonly_fields = ('created_by', 'created_at')


@admin.register(CashDrawer)
class CashDrawerAdmin(ModelAdmin):
    list_display = (
        'cashier', 'opened_at', 'closed_at', 'status',
        'opening_balance', 'closing_balance', 'difference',
    )
    list_filter = (
        'status',
        ('cashier', RelatedDropdownFilter),
    )
    search_fields = ('cashier__username',)
    readonly_fields = ('opened_at', 'closed_at', 'expected_balance', 'difference')
    inlines = [CashTransactionInline]
    ordering = ('-opened_at',)


@admin.register(SupplierBill)
class SupplierBillAdmin(ModelAdmin):
    list_display = (
        'reference', 'supplier', 'amount', 'paid_amount', 'balance_due_display',
        'due_date', 'status', 'created_by', 'approved_by',
    )
    list_filter = (
        'status',
        ('supplier', RelatedDropdownFilter),
        ('created_by', RelatedDropdownFilter),
    )
    search_fields = ('reference', 'supplier__name', 'description', 'notes')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'supplier', 'purchase_order', 'amount', 'due_date', 'description')
        }),
        ('Status', {
            'fields': ('status', 'paid_amount', 'approved_by', 'paid_by', 'payment_method')
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

    def balance_due_display(self, obj):
        return obj.balance_due
    balance_due_display.short_description = 'Balance Due'


@admin.register(FinanceAuditLog)
class FinanceAuditLogAdmin(ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'model_name', 'object_id', 'reference')
    list_filter = (
        'model_name',
        ('user', RelatedDropdownFilter),
    )
    search_fields = ('action', 'reference', 'user__username', 'reason')
    readonly_fields = (
        'user', 'action', 'model_name', 'object_id', 'reference',
        'before', 'after', 'reason', 'ip_address', 'created_at',
    )
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
@admin.register(BankAccount)
class BankAccountAdmin(ModelAdmin):
    list_display = ('account', 'bank_name', 'account_number', 'is_active')
    search_fields = ('bank_name', 'account_number')
    list_filter = ('is_active',)


@admin.register(BankTransaction)
class BankTransactionAdmin(ModelAdmin):
    list_display = ('date', 'bank_account', 'description', 'amount', 'reconciled')
    search_fields = ('description', 'reference')
    list_filter = ('reconciled', 'date')


@admin.register(BankStatement)
class BankStatementAdmin(ModelAdmin):
    list_display = ('account', 'statement_date', 'description', 'amount', 'reconciled')
    list_filter = ('reconciled', 'statement_date')


@admin.register(Reconciliation)
class ReconciliationAdmin(ModelAdmin):
    list_display = ('account', 'statement_date', 'status', 'created_by')
    list_filter = ('status', 'statement_date')


@admin.register(Budget)
class BudgetAdmin(ModelAdmin):
    list_display = ('department', 'fiscal_year', 'amount')
    list_filter = ('fiscal_year', 'department')
    search_fields = ('department__name',)


@admin.register(BudgetLine)
class BudgetLineAdmin(ModelAdmin):
    list_display = ('budget', 'category', 'amount')
    list_filter = ('category',)


@admin.register(FiscalPeriod)
class FiscalPeriodAdmin(ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_closed')
    list_filter = ('is_closed',)