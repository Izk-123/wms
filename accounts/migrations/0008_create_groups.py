from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def create_groups(apps, schema_editor):
    # Get models for permissions
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    # Define groups and their permissions (by codename)
    groups_permissions = {
        'System Administrator': [
            # All permissions – you can grant all, or be selective
            'add_user', 'change_user', 'delete_user', 'view_user',
            'manage_users', 'manage_roles',
            # Inventory
            'view_item', 'add_item', 'change_item', 'delete_item',
            'receive_stock', 'issue_stock', 'transfer_stock', 'adjust_stock',
            'view_stock_report',
            # Procurement
            'view_purchaserequest', 'add_purchaserequest', 'change_purchaserequest', 'delete_purchaserequest',
            'approve_purchaserequest', 'reject_purchaserequest',
            # etc...
        ],
        'Warehouse Manager': [
            'view_item', 'add_item', 'change_item',
            'receive_stock', 'issue_stock', 'transfer_stock', 'adjust_stock',
            'view_stock_report',
            'approve_purchaserequest', 'reject_purchaserequest',
            'approve_materialrequest', 'issue_materialrequest',
            # plus view permissions for procurement, etc.
        ],
        'Storekeeper': [
            'view_item',
            'receive_stock', 'issue_stock', 'transfer_stock', 'adjust_stock',
            'view_stock_report',
        ],
        'Procurement Officer': [
            'view_purchaserequest', 'add_purchaserequest', 'change_purchaserequest',
            # maybe not delete
            'view_supplier', 'add_supplier', 'change_supplier',
            # etc.
        ],
        'Project Supervisor': [
            'view_item',
            'view_materialrequest', 'add_materialrequest', 'change_materialrequest',
            'view_project', 'add_project', 'change_project',
        ],
        'Management': [
            'view_stock_report',
            'view_item',
            # read-only access to reports
        ],
        'Asset Officer': [
            'view_asset', 'add_asset', 'change_asset', 'delete_asset',
            'assign_asset', 'return_asset', 'schedule_maintenance',
        ],
    }

    for group_name, perms in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            # Assign permissions by codename
            for codename in perms:
                try:
                    perm = Permission.objects.get(codename=codename)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    print(f"Permission {codename} not found, skipping")
        else:
            # Optionally update
            pass

def reverse_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[
        'System Administrator', 'Warehouse Manager', 'Storekeeper',
        'Procurement Officer', 'Project Supervisor', 'Management', 'Asset Officer'
    ]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),  # adjust to your latest migration
        # also ensure permissions are created first; you might need to depend on the migrations of other apps
        ('inventory', '0001_initial'),
        ('procurement', '0001_initial'),
        ('operations', '0001_initial'),
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_groups, reverse_groups),
    ]