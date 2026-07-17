import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.utils import IntegrityError
from accounts.models import Role, User
from company_settings.models import Company, SystemSetting, PaymentMethod, Branch
from finance.models import Account
from hr.models import Department, Position, LeaveType, SalaryStructure, SalaryComponent, Employee, EmployeeSalary
from inventory.models import Category, Unit, Warehouse, Item
from procurement.models import Supplier


class Command(BaseCommand):
    help = 'Seed all initial data for J&N ERP: company, accounts, HR, etc.'

    def handle(self, *args, **options):
        self.stdout.write("Starting initial data seeding...")

        # 1. Company Settings
        self.seed_company_settings()

        # 2. Chart of Accounts
        self.seed_chart_of_accounts()

        # 3. HR Data (Departments, Positions, Leave Types, Salary Structure)
        self.seed_hr_data()

        # 4. Inventory Basics (Units, Categories, Warehouses)
        self.seed_inventory_basics()

        # 5. Payment Methods (already in company settings seed)
        # 6. Roles & Groups (sync permissions)
        self.seed_roles_and_groups()

        # 7. Sample Users & Employees
        self.seed_sample_users_and_employees()

        self.stdout.write(self.style.SUCCESS("All initial data seeded successfully."))

    def seed_company_settings(self):
        self.stdout.write("  Seeding company settings...")

        # Check if a company already exists
        company = Company.objects.first()
        if company:
            # Update existing company
            company.name = "J&N Construction & Manufacturing"
            company.trading_name = "J&N WMS"
            company.email = "info@jandn.mw"
            company.phone = "+265 999 000 000"
            company.physical_address = "Blantyre, Malawi"
            company.city = "Blantyre"
            company.country = "Malawi"
            company.currency = "MWK"
            company.currency_symbol = "MK"
            company.timezone = "Africa/Blantyre"
            company.save()
            self.stdout.write("    Company profile updated.")
        else:
            # Create new company
            Company.objects.create(
                name="J&N Construction & Manufacturing",
                trading_name="J&N WMS",
                email="info@jandn.mw",
                phone="+265 999 000 000",
                physical_address="Blantyre, Malawi",
                city="Blantyre",
                country="Malawi",
                currency="MWK",
                currency_symbol="MK",
                timezone="Africa/Blantyre",
            )
            self.stdout.write("    Company profile created.")

        # System Settings (prefixes, tax, etc.)
        defaults = {
            "INVOICE_PREFIX": "INV-",
            "RECEIPT_PREFIX": "REC-",
            "PO_PREFIX": "PO-",
            "PR_PREFIX": "PR-",
            "GRN_PREFIX": "GRN-",
            "SO_PREFIX": "SO-",
            "MR_PREFIX": "MR-",
            "RETURN_PREFIX": "RTN-",
            "EXPENSE_PREFIX": "EXP-",
            "JOURNAL_PREFIX": "JRN-",
            "SKU_PREFIX": "SKU-",
            "ASSET_PREFIX": "AST-",
            "EMP_PREFIX": "EMP-",
            "PAYROLL_PREFIX": "PAY-",
            "DEFAULT_PAYMENT_TERMS": "Net 30",
            "DEFAULT_TAX_RATE": "0.0",
            "ALLOW_NEGATIVE_STOCK": "false",
            "SESSION_TIMEOUT": "28800",
            "AUTO_JOURNAL_REFERENCE": "true",
            "PAYE_TABLE": json.dumps([
                {"min": 0, "max": 100000, "rate": 0},
                {"min": 100000.01, "max": 1000000, "rate": 0.25},
                {"min": 1000000.01, "max": None, "rate": 0.30}
            ]),
            "PENSION_RATE": "0.05",
            "SALARY_EXPENSE_ACCOUNT": "6000",
            "PAYROLL_CASH_ACCOUNT": "1000",
            "PAYE_LIABILITY_ACCOUNT": "2005",
            "PENSION_LIABILITY_ACCOUNT": "2006",
        }
        for key, value in defaults.items():
            setting, created = SystemSetting.objects.get_or_create(key=key, defaults={'value': value})
            if created:
                self.stdout.write(f"    Setting {key} created.")

        # Payment Methods
        methods = [
            ("Cash", "CASH", True, False, 1),
            ("Bank Transfer", "BANK", True, True, 2),
            ("Airtel Money", "AIRTE", True, True, 3),
            ("TNM Mpamba", "MPAMB", True, True, 4),
            ("Cheque", "CHEQUE", True, True, 5),
            ("Credit", "CREDIT", True, False, 6),
        ]
        for name, code, active, ref, order in methods:
            pm, created = PaymentMethod.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'is_active': active,
                    'requires_reference': ref,
                    'order': order
                }
            )
            if created:
                self.stdout.write(f"    Payment method {code} created.")

        # Default Branch (optional)
        branch, created = Branch.objects.get_or_create(
            code="HQ",
            defaults={
                'name': "Head Office - Blantyre",
                'company': company if company else None,
                'address': "Blantyre, Malawi",
                'is_active': True
            }
        )
        if created:
            self.stdout.write("    Default branch created.")

    def seed_chart_of_accounts(self):
        self.stdout.write("  Seeding chart of accounts...")
        accounts = [
            ('1000', 'Cash', 'asset'),
            ('1010', 'Bank Account', 'asset'),
            ('1020', 'Airtel Money', 'asset'),
            ('1030', 'TNM Mpamba', 'asset'),
            ('2005', 'PAYE Liability', 'liability'),
            ('2006', 'Pension Liability', 'liability'),
            ('4000', 'Sales Revenue', 'income'),
            ('6000', 'Salary Expense', 'expense'),
        ]
        for code, name, atype in accounts:
            acc, created = Account.objects.get_or_create(
                code=code,
                defaults={'name': name, 'account_type': atype}
            )
            if created:
                self.stdout.write(f"    Account {code} created.")

    def seed_hr_data(self):
        self.stdout.write("  Seeding HR data...")

        # Departments – use update_or_create to avoid duplicates
        depts = [
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
        for code, name in depts:
            dept, created = Department.objects.update_or_create(
                name=name,
                defaults={'code': code, 'is_active': True}
            )
            if created:
                self.stdout.write(f"    Department {name} created.")
            else:
                self.stdout.write(f"    Department {name} updated.")

        # Leave Types – use update_or_create on code
        leave_types = [
            ('AL', 'Annual Leave', 20),
            ('SL', 'Sick Leave', 10),
            ('ML', 'Maternity Leave', 60),
            ('PL', 'Paternity Leave', 10),
            ('CL', 'Compassionate Leave', 5),
            ('UL', 'Unpaid Leave', 0),
        ]
        for code, name, days in leave_types:
            lt, created = LeaveType.objects.update_or_create(
                code=code,
                defaults={'name': name, 'days_allowed': days, 'is_active': True}
            )
            if created:
                self.stdout.write(f"    Leave type {code} created.")
            else:
                self.stdout.write(f"    Leave type {code} updated.")

        # Salary Structure – update_or_create on name
        structure, created = SalaryStructure.objects.update_or_create(
            name='Standard',
            defaults={'description': 'Standard employee salary structure', 'is_active': True}
        )
        if created:
            self.stdout.write("    Salary structure 'Standard' created.")
        else:
            self.stdout.write("    Salary structure 'Standard' updated.")

        # Salary Components – update_or_create on code
        components = [
            ('BASIC', 'Basic Salary', True, False, False, 'fixed', 0, 0),
            ('HOUSING', 'Housing Allowance', False, True, False, 'fixed', 200000, 0),
            ('TRANSPORT', 'Transport Allowance', False, True, False, 'fixed', 100000, 0),
            ('PAYE', 'PAYE Tax', False, True, True, 'percentage', 0, 'BASIC'),
            ('PENSION', 'Pension', False, True, True, 'percentage', 5, 'BASIC'),
        ]
        for code, name, basic, taxable, ded, calc_type, amount, pct_of in components:
            comp, created = SalaryComponent.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'structure': structure,
                    'is_basic': basic,
                    'is_taxable': taxable,
                    'is_deduction': ded,
                    'calculation_type': calc_type,
                    'amount': amount,
                    'percentage_of': pct_of,
                }
            )
            if created:
                self.stdout.write(f"    Salary component {code} created.")
            else:
                self.stdout.write(f"    Salary component {code} updated.")

    def seed_inventory_basics(self):
        self.stdout.write("  Seeding inventory basics...")

        # Units – update_or_create on name
        units = [
            ('Kilogram', 'kg'),
            ('Litre', 'L'),
            ('Piece', 'pc'),
            ('Box', 'bx'),
            ('Meter', 'm'),
            ('Each', 'ea'),
        ]
        for name, symbol in units:
            unit, created = Unit.objects.update_or_create(
                name=name,
                defaults={'symbol': symbol}
            )
            if created:
                self.stdout.write(f"    Unit {name} created.")
            else:
                self.stdout.write(f"    Unit {name} updated.")

        # Categories – update_or_create on name
        cats = [
            ('Cement & Concrete', 'Cement and concrete products'),
            ('Steel & Iron', 'Steel bars, sheets, etc.'),
            ('Hardware', 'Nuts, bolts, screws, tools'),
            ('Electrical', 'Cables, switches, lighting'),
            ('Plumbing', 'Pipes, fittings, valves'),
            ('Lumber', 'Wood, timber, plywood'),
            ('Paint & Coatings', 'Paints, varnishes, thinners'),
        ]
        for name, desc in cats:
            cat, created = Category.objects.update_or_create(
                name=name,
                defaults={'description': desc}
            )
            if created:
                self.stdout.write(f"    Category {name} created.")
            else:
                self.stdout.write(f"    Category {name} updated.")

        # Warehouses – update_or_create on name
        warehouses = [
            ('Main Warehouse', 'Blantyre Head Office', True),
            ('Lilongwe Depot', 'Lilongwe Branch', True),
            ('Mzuzu Depot', 'Mzuzu Branch', True),
        ]
        for name, loc, active in warehouses:
            wh, created = Warehouse.objects.update_or_create(
                name=name,
                defaults={'location': loc, 'is_active': active}
            )
            if created:
                self.stdout.write(f"    Warehouse {name} created.")
            else:
                self.stdout.write(f"    Warehouse {name} updated.")

    def seed_roles_and_groups(self):
        self.stdout.write("  Seeding roles and groups...")

        # Ensure roles exist – update_or_create on name
        role_names = [
            'System Administrator',
            'Sales Manager',
            'Sales Representative',
            'Cashier',
            'Finance Manager',
            'Accountant',
            'HR Manager',
            'HR Officer',
            'Department Manager',
            'Employee',
        ]
        for name in role_names:
            role, created = Role.objects.update_or_create(name=name)
            if created:
                self.stdout.write(f"    Role {name} created.")
            else:
                self.stdout.write(f"    Role {name} already exists.")

        # Create Django Groups with the same names
        groups = [
            'System Administrator',
            'Sales Manager',
            'Sales Representative',
            'Cashier',
            'Finance Manager',
            'Accountant',
            'HR Manager',
            'HR Officer',
            'Department Manager',
            'Employee',
        ]
        for name in groups:
            group, created = Group.objects.update_or_create(name=name)
            if created:
                self.stdout.write(f"    Group {name} created.")
            else:
                self.stdout.write(f"    Group {name} already exists.")

    def seed_sample_users_and_employees(self):
        self.stdout.write("  Seeding sample users and employees...")

        users_data = [
            ('admin', 'System Administrator', True, 'admin@jandn.mw', 'Admin', 'User'),
            ('salesrep', 'Sales Representative', False, 'sales@jandn.mw', 'John', 'Doe'),
            ('cashier', 'Cashier', False, 'cashier@jandn.mw', 'Jane', 'Doe'),
            ('accountant', 'Accountant', False, 'accountant@jandn.mw', 'Jack', 'Smith'),
            ('financemanager', 'Finance Manager', False, 'finance@jandn.mw', 'Jill', 'Smith'),
            ('hrofficer', 'HR Officer', False, 'hr@jandn.mw', 'Peter', 'Jones'),
            ('hrmanager', 'HR Manager', False, 'hrmanager@jandn.mw', 'Paula', 'Jones'),
            ('employee', 'Employee', False, 'employee@jandn.mw', 'Alice', 'Wonder'),
        ]

        for username, role_name, is_super, email, first, last in users_data:
            # Check if user exists
            user = User.objects.filter(username=username).first()
            if user:
                # Update fields if necessary (but avoid email conflict)
                if user.email != email:
                    # Check if the new email is already taken by another user
                    if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                        self.stdout.write(f"    Email {email} already in use; keeping existing email for {username}.")
                    else:
                        user.email = email
                user.first_name = first
                user.last_name = last
                if is_super and not user.is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                if not is_super and user.is_superuser:
                    user.is_superuser = False
                user.save()
                self.stdout.write(f"    User {username} already exists, updated.")
            else:
                # Create new user
                try:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password='password123',
                        first_name=first,
                        last_name=last,
                        is_staff=True,
                        is_superuser=is_super,
                    )
                    self.stdout.write(f"    User {username} created with email {email}.")
                except IntegrityError:
                    # Email conflict – append a counter
                    counter = 2
                    new_email = email.replace('@', f'{counter}@')
                    while User.objects.filter(email=new_email).exists():
                        counter += 1
                        new_email = email.replace('@', f'{counter}@')
                    user = User.objects.create_user(
                        username=username,
                        email=new_email,
                        password='password123',
                        first_name=first,
                        last_name=last,
                        is_staff=True,
                        is_superuser=is_super,
                    )
                    self.stdout.write(f"    User {username} created with email {new_email} (original {email} was taken).")

            # Assign role
            role = Role.objects.filter(name=role_name).first()
            if role and user.role != role:
                user.role = role
                user.save()

            # Add to group
            group, _ = Group.objects.get_or_create(name=role_name)
            if not user.groups.filter(name=role_name).exists():
                user.groups.add(group)

            # Create employee record (only for non-superusers)
            if not is_super:
                # Get a department and position (if none exist, create placeholders)
                department = Department.objects.filter(is_active=True).first()
                if not department:
                    department = Department.objects.create(name='General', code='GEN', is_active=True)
                position = Position.objects.filter(department=department).first()
                if not position:
                    position = Position.objects.create(name='Employee', department=department)

                employee, created = Employee.objects.update_or_create(
                    user=user,
                    defaults={
                        'first_name': first,
                        'last_name': last,
                        'company_email': user.email,
                        'department': department,
                        'position': position,
                        'date_joined': '2024-01-01',
                        'employment_status': 'active',
                    }
                )
                if created:
                    # Assign salary structure
                    structure = SalaryStructure.objects.filter(is_active=True).first()
                    if structure:
                        EmployeeSalary.objects.update_or_create(employee=employee, defaults={'structure': structure})
                    self.stdout.write(f"    Employee record for {username} created.")
                else:
                    self.stdout.write(f"    Employee record for {username} updated.")