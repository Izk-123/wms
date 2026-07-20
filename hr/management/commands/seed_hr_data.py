from django.core.management.base import BaseCommand
from hr.models import Department, Position, LeaveType, SalaryComponent, SalaryStructure


class Command(BaseCommand):
    help = "Seed initial HR data"

    def handle(self, *args, **kwargs):
        # Create departments
        departments = [
            ('ADM', 'Administration'),
            ('FIN', 'Finance'),
            ('HR', 'Human Resources'),
            ('SAL', 'Sales'),
            ('PROC', 'Procurement'),
            ('WARE', 'Warehouse'),
            ('CON', 'Construction'),
            ('MFG', 'Manufacturing'),
            ('ICT', 'ICT'),
            ('SEC', 'Security'),
        ]
        for code, name in departments:
            dept, created = Department.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True}
            )
            self.stdout.write(f"{'Created' if created else 'Already exists'} Department: {code}")

        # Create leave types
        leave_types = [
            ('AL', 'Annual Leave', 20),
            ('SL', 'Sick Leave', 10),
            ('ML', 'Maternity Leave', 60),
            ('PL', 'Paternity Leave', 10),
            ('CL', 'Compassionate Leave', 5),
            ('UL', 'Unpaid Leave', 0),
        ]
        for code, name, days in leave_types:
            lt, created = LeaveType.objects.get_or_create(
                code=code,
                defaults={'name': name, 'days_allowed': days, 'is_active': True}
            )
            self.stdout.write(f"{'Created' if created else 'Already exists'} Leave Type: {code}")

        self.stdout.write(self.style.SUCCESS("HR data seeded."))
        
        # Create default salary structure
        structure, _ = SalaryStructure.objects.get_or_create(
            name='Standard',
            defaults={'description': 'Standard employee salary structure', 'is_active': True}
        )

        # Create components
        components = [
            ('BASIC', 'Basic Salary', structure, True, False, False, 'fixed', 0, 0),
            ('HOUSING', 'Housing Allowance', structure, False, True, False, 'fixed', 200000, 0),
            ('TRANSPORT', 'Transport Allowance', structure, False, True, False, 'fixed', 100000, 0),
            ('PAYE', 'PAYE Tax', structure, False, True, True, 'percentage', 0, 'BASIC'),
            ('PENSION', 'Pension', structure, False, True, True, 'percentage', 5, 'BASIC'),
        ]
        for code, name, struct, basic, taxable, ded, calc_type, amount, pct_of in components:
            SalaryComponent.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'structure': struct,
                    'is_basic': basic,
                    'is_taxable': taxable,
                    'is_deduction': ded,
                    'calculation_type': calc_type,
                    'amount': amount,
                    'percentage_of': pct_of,
                }
            )