from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from accounts.models import User


class Command(BaseCommand):
    help = 'Assign users to Django Groups based on their Role'

    ROLE_GROUP_MAP = {
        'System Administrator': 'System Administrator',
        'Warehouse Manager':    'Warehouse Manager',
        'Storekeeper':          'Storekeeper',
        'Procurement Officer':  'Procurement Officer',
        'Project Supervisor':   'Project Supervisor',
        'Asset Officer':        'Asset Officer',
        'Management':           'Management',
    }
    
    # In your group sync script
    group_permissions = {
        'System Administrator': [
            'hr.view_department', 'hr.add_department', 'hr.change_department', 'hr.delete_department',
            'hr.view_position', 'hr.add_position', 'hr.change_position', 'hr.delete_position',
            'hr.view_employee', 'hr.add_employee', 'hr.change_employee', 'hr.delete_employee',
            'hr.view_leaverequest', 'hr.add_leaverequest', 'hr.manage_leave',
            'hr.view_attendance', 'hr.manage_attendance',
        ],
        'HR Manager': [
            'hr.view_department', 'hr.change_department',
            'hr.view_position', 'hr.change_position',
            'hr.view_employee', 'hr.add_employee', 'hr.change_employee',
            'hr.view_leaverequest', 'hr.manage_leave',
            'hr.view_attendance',
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
            'hr.view_leaverequest', 'hr.manage_leave',  # Can approve leave for their department
            'hr.view_attendance',
        ],
        'Employee': [
            'hr.view_leaverequest', 'hr.add_leaverequest',
            'hr.view_attendance',
        ],
    }

    def handle(self, *args, **options):
        for user in User.objects.select_related('role').all():
            if not user.role:
                self.stdout.write(f"  Skipped (no role): {user.username}")
                continue

            group_name = self.ROLE_GROUP_MAP.get(user.role.name)
            if not group_name:
                self.stdout.write(
                    f"  No mapping for role: {user.role.name}"
                )
                continue

            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {user.username} → {group_name}"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nGroup sync complete."))