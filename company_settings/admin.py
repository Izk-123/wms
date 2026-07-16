from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RelatedDropdownFilter
from .models import ApprovalRequest, ApprovalRule, Company, Branch, SystemSetting, PaymentMethod

@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = ("name", "email", "phone", "currency")
    fieldsets = (
        ("General", {
            "fields": ("name", "trading_name", "registration_number", "tax_id")
        }),
        ("Contact", {
            "fields": ("email", "phone", "website")
        }),
        ("Address", {
            "fields": ("physical_address", "postal_address", "city", "country")
        }),
        ("Localization", {
            "fields": ("timezone", "currency", "currency_symbol")
        }),
        ("Branding", {
            "fields": ("logo", "favicon")
        }),
    )


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    list_display = ("name", "code", "company", "is_active")
    list_filter = ("is_active", ("company", RelatedDropdownFilter))


@admin.register(PaymentMethod)
class PaymentMethodAdmin(ModelAdmin):
    list_display = ("name", "code", "is_active", "order")
    list_editable = ("is_active", "order")


@admin.register(SystemSetting)
class SystemSettingAdmin(ModelAdmin):
    list_display = ("key", "value", "is_boolean")
    search_fields = ("key",)
    

@admin.register(ApprovalRule)
class ApprovalRuleAdmin(ModelAdmin):
    list_display = ('action', 'min_amount', 'max_amount', 'required_role', 'is_active', 'order')
    list_filter = ('action', 'is_active', 'required_role')
    search_fields = ('action', 'required_role__name')

@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(ModelAdmin):
    list_display = ('action', 'reference', 'amount', 'requested_by', 'status', 'requested_at')
    list_filter = ('action', 'status', 'requested_at')
    search_fields = ('reference', 'requested_by__username')
    readonly_fields = ('requested_at',)
    fieldsets = (
        (None, {
            'fields': ('action', 'reference', 'amount', 'status')
        }),
        ('Approval Details', {
            'fields': ('requested_by', 'requested_at', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Related Document', {
            'fields': ('content_type', 'object_id')
        }),
    )