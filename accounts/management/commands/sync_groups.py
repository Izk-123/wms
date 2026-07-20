from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from accounts.models import User


class Command(BaseCommand):
    help = 'Assign users to Django Groups based on their Role and sync permissions'

    # Map each Role name (as stored in accounts.Role) to a Django Group name
    ROLE_GROUP_MAP = {
        'System Administrator': 'System Administrator',
        'Sales Manager': 'Sales Manager',
        'Sales Representative': 'Sales Representative',
        'Cashier': 'Cashier',
        'Finance Manager': 'Finance Manager',
        'Accountant': 'Accountant',
        'HR Manager': 'HR Manager',
        'HR Officer': 'HR Officer',
        'Department Manager': 'Department Manager',
        'Employee': 'Employee',
        # Existing roles (if any)
        'Warehouse Manager': 'Warehouse Manager',
        'Storekeeper': 'Storekeeper',
        'Procurement Officer': 'Procurement Officer',
        'Project Supervisor': 'Project Supervisor',
        'Asset Officer': 'Asset Officer',
        'Management': 'Management',
    }

    # Permissions assigned to each group
    GROUP_PERMISSIONS = {
        'System Administrator': [
            # Inventory
            'inventory.view_item', 'inventory.add_item', 'inventory.change_item', 'inventory.delete_item',
            'inventory.receive_stock', 'inventory.issue_stock', 'inventory.transfer_stock', 'inventory.adjust_stock',
            'inventory.view_stock_report',
            # Procurement
            'procurement.view_supplier', 'procurement.add_supplier', 'procurement.change_supplier', 'procurement.delete_supplier',
            'procurement.view_purchaserequest', 'procurement.add_purchaserequest', 'procurement.change_purchaserequest',
            'procurement.approve_purchaserequest', 'procurement.reject_purchaserequest',
            'procurement.view_purchaseorder', 'procurement.add_purchaseorder', 'procurement.change_purchaseorder',
            'procurement.confirm_goodsreceipt',
            # Operations
            'operations.view_project', 'operations.add_project', 'operations.change_project', 'operations.delete_project',
            'operations.view_materialrequest', 'operations.add_materialrequest', 'operations.change_materialrequest',
            'operations.approve_materialrequest', 'operations.issue_materialrequest',
            # Sales
            'sales.view_customer', 'sales.add_customer', 'sales.change_customer', 'sales.delete_customer',
            'sales.view_salesorder', 'sales.add_salesorder', 'sales.change_salesorder', 'sales.delete_salesorder',
            'sales.approve_discount',
            'sales.view_invoice', 'sales.create_invoice', 'sales.change_invoice', 'sales.cancel_invoice',
            'sales.receive_payment', 'sales.view_payment', 'sales.delete_payment',
            # Finance
            'finance.view_account', 'finance.add_account', 'finance.change_account', 'finance.delete_account',
            'finance.view_journalentry', 'finance.approve_journalentry',
            'finance.add_expense', 'finance.view_expense', 'finance.approve_expense', 'finance.pay_expense',
            # HR
            'hr.view_department', 'hr.add_department', 'hr.change_department', 'hr.delete_department',
            'hr.view_position', 'hr.add_position', 'hr.change_position', 'hr.delete_position',
            'hr.view_employee', 'hr.add_employee', 'hr.change_employee', 'hr.delete_employee',
            'hr.view_leaverequest', 'hr.add_leaverequest', 'hr.manage_leave',
            'hr.view_attendance', 'hr.manage_attendance',
            'hr.view_payrollrun', 'hr.add_payrollrun', 'hr.change_payrollrun', 'hr.delete_payrollrun',
            'hr.process_payrollrun', 'hr.post_payrollrun', 'hr.view_payslip',
            # Assets
            'assets.view_asset', 'assets.add_asset', 'assets.change_asset', 'assets.delete_asset',
            'assets.assign_asset', 'assets.return_asset', 'assets.schedule_maintenance',
        ],
        'Sales Manager': [
            'sales.view_customer', 'sales.add_customer', 'sales.change_customer',
            'sales.view_salesorder', 'sales.add_salesorder', 'sales.change_salesorder',
            'sales.approve_discount',
            'sales.view_invoice', 'sales.create_invoice', 'sales.change_invoice',
            'inventory.view_item',
            'reports.view_salesreport',
        ],
        'Sales Representative': [
            'sales.view_customer', 'sales.add_customer', 'sales.change_customer',
            'sales.view_salesorder', 'sales.add_salesorder', 'sales.change_salesorder',
            'sales.view_invoice',
            'inventory.view_item',
        ],
        'Cashier': [
            'sales.view_invoice',
            'sales.receive_payment', 'sales.view_payment',
        ],
        'Finance Manager': [
            'finance.view_account', 'finance.add_account', 'finance.change_account',
            'finance.view_journalentry', 'finance.approve_journalentry',
            'finance.add_expense', 'finance.view_expense', 'finance.approve_expense', 'finance.pay_expense',
            'inventory.view_stock_report',
            'sales.view_invoice',
            'reports.view_financereport',
        ],
        'Accountant': [
            'finance.view_account',
            'finance.view_journalentry',
            'finance.add_expense', 'finance.view_expense', 'finance.pay_expense',
        ],
        'HR Manager': [
            'hr.view_department', 'hr.change_department',
            'hr.view_position', 'hr.change_position',
            'hr.view_employee', 'hr.add_employee', 'hr.change_employee',
            'hr.view_leaverequest', 'hr.manage_leave',
            'hr.view_attendance', 'hr.manage_attendance',
            'hr.view_payrollrun', 'hr.add_payrollrun', 'hr.process_payrollrun', 'hr.post_payrollrun',
        ],
        'HR Officer': [
            'hr.view_department',
            'hr.view_position',
            'hr.view_employee', 'hr.add_employee', 'hr.change_employee',
            'hr.view_leaverequest', 'hr.add_leaverequest',
            'hr.view_attendance',
        ],
        'Department Manager': [
            'hr.view_employee',
            'hr.view_leaverequest', 'hr.manage_leave',
            'hr.view_attendance',
        ],
        'Employee': [
            'hr.view_leaverequest', 'hr.add_leaverequest',
            'hr.view_attendance',
        ],
        # Existing roles can be added as needed
        'Warehouse Manager': [
            'inventory.view_item', 'inventory.receive_stock', 'inventory.issue_stock', 'inventory.transfer_stock',
            'inventory.adjust_stock', 'inventory.view_stock_report',
            'procurement.approve_purchaserequest',
            'operations.approve_materialrequest',
        ],
        'Storekeeper': [
            'inventory.view_item', 'inventory.receive_stock', 'inventory.issue_stock',
            'inventory.view_stock_report',
        ],
        'Procurement Officer': [
            'procurement.view_supplier', 'procurement.add_supplier', 'procurement.change_supplier',
            'procurement.view_purchaserequest', 'procurement.add_purchaserequest', 'procurement.change_purchaserequest',
            'procurement.view_purchaseorder', 'procurement.add_purchaseorder', 'procurement.change_purchaseorder',
        ],
        'Project Supervisor': [
            'operations.view_project', 'operations.add_project', 'operations.change_project',
            'operations.view_materialrequest', 'operations.add_materialrequest', 'operations.change_materialrequest',
            'inventory.view_item',
        ],
        'Asset Officer': [
            'assets.view_asset', 'assets.add_asset', 'assets.change_asset',
            'assets.assign_asset', 'assets.return_asset', 'assets.schedule_maintenance',
        ],
        'Management': [
            'inventory.view_stock_report',
            'sales.view_invoice',
            'finance.view_journalentry',
            'hr.view_employee',
        ],
    }

    def handle(self, *args, **options):
        # 1. Assign users to groups based on their Role
        self.stdout.write("Assigning users to groups...")
        for user in User.objects.select_related('role').all():
            if not user.role:
                self.stdout.write(f"  Skipped (no role): {user.username}")
                continue

            group_name = self.ROLE_GROUP_MAP.get(user.role.name)
            if not group_name:
                self.stdout.write(f"  No mapping for role: {user.role.name}")
                continue

            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f"  {user.username} → {group_name}"))

        # 2. Assign permissions to groups
        self.stdout.write("\nAssigning permissions to groups...")
        for group_name, perm_codenames in self.GROUP_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            for codename in perm_codenames:
                try:
                    perm = Permission.objects.get(codename=codename)
                    group.permissions.add(perm)
                    self.stdout.write(f"  Added {codename} to {group_name}")
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Permission {codename} not found, skipping"))

        self.stdout.write(self.style.SUCCESS("\nGroup sync complete."))