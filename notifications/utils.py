from django.contrib.auth.models import Permission
from accounts.models import User


def get_users_with_permission(permission_codename, app_label):
    """
    Returns all active users who have a specific permission,
    either directly or through a group.
    """
    perm_string = f"{app_label}.{permission_codename}"

    return [
        user for user in User.objects.filter(
            is_active=True
        ).select_related('role')
        if user.has_perm(perm_string)
    ]


def get_warehouse_managers():
    return get_users_with_permission(
        'approve_purchaserequest', 'procurement'
    )


def get_procurement_officers():
    return get_users_with_permission(
        'add_purchaseorder', 'procurement'
    )


def get_material_request_approvers():
    return get_users_with_permission(
        'approve_materialrequest', 'operations'
    )