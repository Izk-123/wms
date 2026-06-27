"""
accounts/admin.py
Admin configuration for all accounts models:
- Role
- User (custom, with auto‑generated employee numbers)
- LoginHistory (audit log)
- UserActivity (audit log)
All use Unfold's ModelAdmin for a modern UI.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin
from .models import Role, User, LoginHistory, UserActivity


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    """Role admin: list, search, and optional inline users."""
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(User)
class CustomUserAdmin(ModelAdmin, UserAdmin):
    """
    Custom User admin.
    - employee_number is displayed and searchable.
    - Auto‑generated on creation (model handles it).
    """
    list_display = (
        'username', 'email', 'employee_number',
        'role', 'is_active', 'must_change_password'
    )
    list_filter = ('role', 'is_active')
    search_fields = (
        'username', 'email', 'employee_number',
        'first_name', 'last_name'
    )

    # Group fields into sections
    fieldsets = UserAdmin.fieldsets + (
        ('J&N Info', {
            'fields': (
                'role', 'phone', 'employee_number',
                'must_change_password', 'is_first_login'
            )
        }),
    )

    # If you prefer not to allow manual changes to employee_number:
    # readonly_fields = ('employee_number',)


@admin.register(LoginHistory)
class LoginHistoryAdmin(ModelAdmin):
    """
    Login history – read‑only log of user logins.
    """
    list_display = ('user', 'login_time', 'ip_address')
    list_filter = ('login_time',)
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'login_time')
    ordering = ('-login_time',)

    # Disable add/delete permissions (view-only)
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # optionally allow superusers to delete if needed


@admin.register(UserActivity)
class UserActivityAdmin(ModelAdmin):
    """
    User activity log – read‑only audit trail of user actions.
    """
    list_display = ('user', 'action', 'module', 'created_at')
    list_filter = ('module', 'created_at')
    search_fields = ('user__username', 'user__email', 'action', 'module')
    readonly_fields = ('user', 'action', 'module', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # optional