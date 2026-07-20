from django.db import models
from django.core.validators import MinLengthValidator, EmailValidator
from django.contrib.auth import get_user_model
from company_settings.models import Branch
from company_settings.numbering import generate_next_number

User = get_user_model()


class Department(models.Model):
    """Organisational departments."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Position(models.Model):
    """Job positions/titles within the organisation."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='positions'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Core employee record – linked to a User account via OneToOne."""
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    EMPLOYMENT_STATUS_CHOICES = (
        ('active', 'Active'),
        ('probation', 'Probation'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
        ('resigned', 'Resigned'),
    )

    EMPLOYMENT_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('casual', 'Casual'),
        ('intern', 'Intern'),
    )

    # ── Link to User (authentication) ──────────────────
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile',
        help_text="Link to system user account. Leave blank if no login required."
    )

    # ── Basic Information ──────────────────────────────
    employee_id = models.CharField(max_length=50, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    passport_number = models.CharField(max_length=50, blank=True)

    # ── Contact Information ─────────────────────────────
    company_email = models.EmailField(unique=True)
    personal_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    physical_address = models.TextField(blank=True)

    # ── Emergency Contact ──────────────────────────────
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    # ── Employment Details ──────────────────────────────
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='active'
    )
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='full_time'
    )
    date_joined = models.DateField()
    date_left = models.DateField(null=True, blank=True)

    # ── Additional Information ──────────────────────────
    profile_photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # ── Audit ────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        permissions = [
            ("manage_attendance", "Can manage attendance"),
            ("manage_leave", "Can manage leave requests"),
            ("view_payrollrun", "Can view payroll runs"),
            ("add_payrollrun", "Can add payroll runs"),
            ("change_payrollrun", "Can change payroll runs"),
            ("delete_payrollrun", "Can delete payroll runs"),
            ("process_payrollrun", "Can process payroll runs"),
            ("post_payrollrun", "Can post payroll runs to Finance"),
            ("view_payslip", "Can view payslips"),
        ]
        
        

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = generate_next_number(
                "EMP_ID_PREFIX",
                Employee,
                field="employee_id",
                padding=5
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hr:employee-detail', kwargs={'pk': self.pk})


class EmploymentHistory(models.Model):
    """Track changes in employment status, position, department, etc."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employment_history')
    change_date = models.DateField(auto_now_add=True)
    field = models.CharField(max_length=50)  # e.g., position, department, status
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255)
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-change_date']

    def __str__(self):
        return f"{self.employee.full_name} – {self.field} changed"


class LeaveType(models.Model):
    """Types of leave (Annual, Sick, Maternity, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    days_allowed = models.PositiveIntegerField(default=0, help_text="Annual entitlement")
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """Employee leave requests with approval workflow."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1, help_text="Number of days (e.g., 0.5 for half-day)")
    reason = models.TextField(blank=True)
    attachment = models.FileField(upload_to='leave_attachments/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leave')
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.employee.full_name} – {self.leave_type.name} ({self.start_date})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('hr:leave-detail', kwargs={'pk': self.pk})


class Attendance(models.Model):
    """Daily attendance records."""
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='attendance')
    date = models.DateField(auto_now_add=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    is_overtime = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', '-clock_in']
        unique_together = ['employee', 'date']

    def __str__(self):
        return f"{self.employee.full_name} – {self.date}"

    @property
    def hours_worked(self):
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            return delta.total_seconds() / 3600
        return 0


class EmployeeDocument(models.Model):
    """Documents related to an employee (contract, ID, certificates, etc.)"""
    DOCUMENT_TYPES = (
        ('contract', 'Employment Contract'),
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('certificate', 'Certificate'),
        ('cv', 'CV'),
        ('medical', 'Medical Certificate'),
        ('driving_licence', 'Driving Licence'),
        ('other', 'Other'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='employee_documents/')
    description = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.employee.full_name} – {self.title}"
    
# ─── Salary & Payroll ────────────────────────────────────────

class SalaryStructure(models.Model):
    """Defines a collection of salary components (e.g., 'Standard', 'Executive')."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class SalaryComponent(models.Model):
    """Individual component: Basic, Housing, Transport, PAYE, Pension, etc."""
    CALCULATION_TYPES = (
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of another component'),
    )

    structure = models.ForeignKey(SalaryStructure, on_delete=models.CASCADE, related_name='components')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)  # e.g., BASIC, HOUSING, PAYE
    is_basic = models.BooleanField(default=False)
    is_taxable = models.BooleanField(default=True)
    is_deduction = models.BooleanField(default=False)  # True for deductions (PAYE, Pension)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPES, default='fixed')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # for fixed
    percentage_of = models.CharField(max_length=20, blank=True)  # e.g., 'BASIC' (code of parent)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.code} – {self.name}"


class EmployeeSalary(models.Model):
    """Current salary assignment for an employee."""
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary')
    structure = models.ForeignKey(SalaryStructure, on_delete=models.PROTECT)
    effective_date = models.DateField(auto_now_add=True)
    # Optionally store actual component values (if different from structure defaults)
    # We'll keep it simple: use structure defaults for now.

    def __str__(self):
        return f"{self.employee.full_name} – {self.structure.name}"


class PayrollRun(models.Model):
    """A payroll period (monthly/weekly) for a group of employees."""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('processed', 'Processed'),
        ('posted', 'Posted to Finance'),
        ('cancelled', 'Cancelled'),
    )
    reference = models.CharField(max_length=50, unique=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    run_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='payroll_runs')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-run_date']

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_next_number("PAYROLL_PREFIX", PayrollRun, padding=6)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} – {self.period_start} to {self.period_end}"


class PayrollItem(models.Model):
    """Individual employee entry in a payroll run."""
    payroll = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='items')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT)
    # Calculated fields
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    paye = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    pension = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    # Breakdown in JSON for reference
    breakdown = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.employee.full_name} – {self.payroll.reference}"


class Payslip(models.Model):
    """Stored payslip (PDF) for each payroll item."""
    payroll_item = models.OneToOneField(PayrollItem, on_delete=models.CASCADE, related_name='payslip')
    pdf_file = models.FileField(upload_to='payslips/')
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip – {self.payroll_item.employee.full_name} ({self.payroll_item.payroll.reference})"