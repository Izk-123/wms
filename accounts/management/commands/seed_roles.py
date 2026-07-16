from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'Create default roles for J&N WMS'

    def handle(self, *args, **kwargs):
        roles = [
            ("System Administrator", "Full system access, user and role management."),
            ("Warehouse Manager", "Approve stock movements, monitor inventory levels."),
            ("Storekeeper", "Receive goods, issue materials, perform stock counts."),
            ("Procurement Officer", "Manage suppliers, purchase orders, and deliveries."),
            ("Project Supervisor", "Request and track materials for construction projects."),
            ("Asset Officer", "Manage tools, equipment assignments, and maintenance."),
            ("Management", "Read-only access to dashboards and reports."),
        ]

        for name, description in roles:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created role: {name}"))
            else:
                self.stdout.write(f"  Already exists: {name}")

        self.stdout.write(self.style.SUCCESS("\nAll roles ready."))