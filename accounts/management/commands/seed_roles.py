from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'Create default roles for J&N WMS with levels'

    def handle(self, *args, **kwargs):
        # Roles with levels (higher number = more authority)
        roles = [
            # System
            ("System Administrator", 99, "Full system access, user and role management."),

            # Sales
            ("Sales Manager", 50, "Manage sales team, approve discounts, review sales performance."),
            ("Sales Representative", 20, "Create quotations, sales orders, manage customers."),

            # Finance
            ("Finance Manager", 60, "Approve payments, expenses, review financial reports."),
            ("Accountant", 40, "Record accounting entries, bank reconciliation, prepare financial reports."),
            ("Cashier", 30, "Receive customer payments, issue receipts."),

            # HR
            ("HR Manager", 55, "Full HR access: employees, leave, payroll."),
            ("HR Officer", 35, "Manage employee records, leave, attendance."),
            ("Department Manager", 45, "Approve leave for department staff."),
            ("Employee", 10, "Self-service: view profile, apply leave, view payslips."),

            # Existing roles (preserve them)
            ("Warehouse Manager", 50, "Approve stock movements, monitor inventory levels."),
            ("Storekeeper", 25, "Receive goods, issue materials, perform stock counts."),
            ("Procurement Officer", 30, "Manage suppliers, purchase orders, and deliveries."),
            ("Project Supervisor", 30, "Request and track materials for construction projects."),
            ("Asset Officer", 30, "Manage tools, equipment assignments, and maintenance."),
            ("Management", 40, "Read-only access to dashboards and reports."),
        ]

        for name, level, description in roles:
            role, created = Role.objects.update_or_create(
                name=name,
                defaults={'description': description, 'level': level}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created role: {name} (level {level})"))
            else:
                self.stdout.write(f"  Updated role: {name} (level {level})")

        self.stdout.write(self.style.SUCCESS("\nAll roles ready."))