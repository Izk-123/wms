from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def add_permissions(apps, schema_editor):
    # Get models for permissions
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    # Define which groups get which permissions
    group_permissions = {
        'System Administrator': [
            # Sales permissions
            'add_salesorder', 'change_salesorder', 'view_salesorder', 'delete_salesorder',
            'approve_discount',
            'create_invoice', 'view_invoice', 'change_invoice', 'cancel_invoice',
            'receive_payment', 'view_payment', 'delete_payment',
            # Finance permissions
            'add_account', 'change_account', 'view_account', 'delete_account',
            'view_journalentry', 'approve_journalentry',
            'add_expense', 'view_expense', 'approve_expense', 'pay_expense',
        ],
        'Sales Manager': [
            'view_salesorder', 'change_salesorder',
            'approve_discount',
            'view_invoice', 'create_invoice', 'change_invoice',
            'view_payment',
        ],
        'Sales Representative': [
            'add_salesorder', 'view_salesorder', 'change_salesorder',
            'view_invoice',
        ],
        'Cashier': [
            'view_invoice', 'receive_payment', 'view_payment',
        ],
        'Finance Manager': [
            'view_account', 'add_account', 'change_account',
            'view_journalentry', 'approve_journalentry',
            'add_expense', 'view_expense', 'approve_expense', 'pay_expense',
        ],
        'Accountant': [
            'view_account',
            'view_journalentry',
            'add_expense', 'view_expense', 'pay_expense',
        ],
        'Warehouse Manager': [
            'view_salesorder', 'view_invoice',  # read-only
        ],
        'Management': [
            'view_salesorder', 'view_invoice', 'view_expense',
        ],
    }

    for group_name, perm_codenames in group_permissions.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        for codename in perm_codenames:
            try:
                perm = Permission.objects.get(codename=codename)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                # Permission might not exist yet; skip or print warning
                print(f"Permission {codename} not found, skipping")

def reverse_permissions(apps, schema_editor):
    # Optional: remove these permissions from groups (not required)
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_merge_20260626_0839'),  # adjust to your last migration
        ('sales', '0001_initial'),               # ensure sales permissions exist
        ('finance', '0001_initial'),             # ensure finance permissions exist
    ]

    operations = [
        migrations.RunPython(add_permissions, reverse_permissions),
    ]