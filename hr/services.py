from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.db import models
from .models import Employee, LeaveRequest, Attendance
import json
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from company_settings.services import get_setting
from finance.models import Account, JournalEntry, JournalLine
from .models import (
    SalaryStructure, SalaryComponent, EmployeeSalary,
    PayrollRun, PayrollItem, Payslip
)
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from django.core.files.base import ContentFile
from django.conf import settings


def get_employee_salary_breakdown(employee, pay_date=None):
    """
    Calculate the salary breakdown for a single employee.
    Returns dict with components and totals.
    """
    salary = employee.salary
    structure = salary.structure
    components = structure.components.all()

    # Build component values
    component_values = {}
    basic = Decimal('0.00')
    allowances = Decimal('0.00')
    deductions = Decimal('0.00')

    for comp in components:
        if comp.calculation_type == 'fixed':
            value = comp.amount
        elif comp.calculation_type == 'percentage' and comp.percentage_of:
            base_value = component_values.get(comp.percentage_of, Decimal('0.00'))
            value = (base_value * comp.amount) / 100  # amount is percentage
        else:
            value = Decimal('0.00')

        component_values[comp.code] = value
        if comp.is_basic:
            basic += value
        elif comp.is_deduction:
            deductions += value
        else:
            allowances += value

    gross = basic + allowances
    total_deductions = deductions

    # Apply PAYE and pension if not already defined in components
    # If not, we can calculate them separately and add to deductions
    if 'PAYE' not in component_values:
        paye = calculate_paye(gross)
    else:
        paye = component_values.get('PAYE', Decimal('0.00'))

    if 'PENSION' not in component_values:
        pension_rate = Decimal(get_setting('PENSION_RATE', '0.05'))
        pension = basic * pension_rate
    else:
        pension = component_values.get('PENSION', Decimal('0.00'))

    total_deductions += paye + pension

    net = gross - total_deductions

    return {
        'basic': basic,
        'allowances': allowances,
        'gross': gross,
        'deductions': {
            'paye': paye,
            'pension': pension,
            'other': total_deductions - paye - pension,
        },
        'net': net,
        'breakdown': component_values,
    }


def calculate_paye(gross):
    """Calculate PAYE based on tax bands from settings."""
    table_json = get_setting('PAYE_TABLE', '[]')
    try:
        table = json.loads(table_json)
    except json.JSONDecodeError:
        table = []

    tax = Decimal('0.00')
    for band in table:
        min_amt = Decimal(band.get('min', 0))
        max_amt = Decimal(band.get('max', 0)) if band.get('max') else None
        rate = Decimal(band.get('rate', 0))
        if gross > min_amt:
            taxable = gross - min_amt
            if max_amt and gross > max_amt:
                taxable = max_amt - min_amt
            tax += taxable * rate
    return tax


@transaction.atomic
def process_payroll(payroll_run):
    """Calculate payroll for all active employees."""
    if payroll_run.status != 'draft':
        raise ValidationError("Only draft payroll runs can be processed.")

    employees = Employee.objects.filter(is_active=True, employment_status='active')

    if not employees.exists():
        raise ValidationError("No active employees found.")

    total_gross = Decimal('0.00')
    total_net = Decimal('0.00')

    for emp in employees:
        try:
            breakdown = get_employee_salary_breakdown(emp)
        except EmployeeSalary.DoesNotExist:
            continue  # skip employees without salary setup

        payroll_item = PayrollItem.objects.create(
            payroll=payroll_run,
            employee=emp,
            basic_salary=breakdown['basic'],
            allowances=breakdown['allowances'],
            gross_pay=breakdown['gross'],
            paye=breakdown['deductions']['paye'],
            pension=breakdown['deductions']['pension'],
            other_deductions=breakdown['deductions']['other'],
            total_deductions=breakdown['deductions']['paye'] + breakdown['deductions']['pension'] + breakdown['deductions']['other'],
            net_pay=breakdown['net'],
            breakdown=breakdown['breakdown'],
        )

        total_gross += breakdown['gross']
        total_net += breakdown['net']

        # Generate payslip PDF immediately
        generate_payslip_pdf(payroll_item)

    payroll_run.status = 'processed'
    payroll_run.save()

    return payroll_run


def generate_payslip_pdf(payroll_item):
    """Generate a PDF payslip and save to Payslip model."""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    # Draw header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(2*cm, 27*cm, "J&N WMS – Payslip")

    p.setFont("Helvetica", 10)
    p.drawString(2*cm, 26*cm, f"Payroll: {payroll_item.payroll.reference}")
    p.drawString(2*cm, 25.5*cm, f"Employee: {payroll_item.employee.full_name}")
    p.drawString(2*cm, 25*cm, f"Employee ID: {payroll_item.employee.employee_id}")
    p.drawString(2*cm, 24.5*cm, f"Period: {payroll_item.payroll.period_start} – {payroll_item.payroll.period_end}")

    # Draw table (simplified)
    y = 23
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y*cm, "Description")
    p.drawString(12*cm, y*cm, "Amount")

    y -= 0.5
    p.setFont("Helvetica", 9)
    items = [
        ("Basic Salary", payroll_item.basic_salary),
        ("Allowances", payroll_item.allowances),
        ("Gross Pay", payroll_item.gross_pay),
        ("PAYE", -payroll_item.paye),
        ("Pension", -payroll_item.pension),
        ("Other Deductions", -payroll_item.other_deductions),
        ("Total Deductions", -payroll_item.total_deductions),
        ("Net Pay", payroll_item.net_pay),
    ]
    for label, amount in items:
        p.drawString(2*cm, y*cm, label)
        p.drawString(12*cm, y*cm, f"MWK {amount:,.2f}")
        y -= 0.5

    # Footer
    p.setFont("Helvetica", 8)
    p.drawString(2*cm, 1*cm, "This is a computer-generated payslip. No signature required.")

    p.showPage()
    p.save()

    buffer.seek(0)
    filename = f"payslip_{payroll_item.employee.employee_id}_{payroll_item.payroll.reference}.pdf"
    content = ContentFile(buffer.read(), name=filename)

    payslip = Payslip.objects.create(
        payroll_item=payroll_item,
        pdf_file=content
    )
    return payslip


@transaction.atomic
def post_payroll_to_finance(payroll_run):
    """Create journal entries for the payroll run."""
    if payroll_run.status != 'processed':
        raise ValidationError("Only processed payroll runs can be posted.")

    if payroll_run.status == 'posted':
        raise ValidationError("This payroll is already posted.")

    # Get accounts from settings
    expense_code = get_setting('SALARY_EXPENSE_ACCOUNT', '6000')
    cash_code = get_setting('PAYROLL_CASH_ACCOUNT', '1000')
    paye_code = get_setting('PAYE_LIABILITY_ACCOUNT', '2005')
    pension_code = get_setting('PENSION_LIABILITY_ACCOUNT', '2006')

    expense_account = Account.objects.get(code=expense_code)
    cash_account = Account.objects.get(code=cash_code)
    paye_account = Account.objects.get(code=paye_code)
    pension_account = Account.objects.get(code=pension_code)

    # Calculate totals
    total_gross = payroll_run.items.aggregate(total=Sum('gross_pay'))['total'] or Decimal('0.00')
    total_net = payroll_run.items.aggregate(total=Sum('net_pay'))['total'] or Decimal('0.00')
    total_paye = payroll_run.items.aggregate(total=Sum('paye'))['total'] or Decimal('0.00')
    total_pension = payroll_run.items.aggregate(total=Sum('pension'))['total'] or Decimal('0.00')

    # Create journal entry
    entry = JournalEntry.objects.create(
        description=f"Payroll {payroll_run.reference} – {payroll_run.period_start} to {payroll_run.period_end}",
        reference=payroll_run.reference,
        created_by=payroll_run.created_by,
    )

    # Debit salary expense
    JournalLine.objects.create(
        entry=entry,
        account=expense_account,
        debit=total_gross,
        description=f"Gross salaries {payroll_run.reference}"
    )

    # Credit net pay to cash/bank
    JournalLine.objects.create(
        entry=entry,
        account=cash_account,
        credit=total_net,
        description=f"Net pay {payroll_run.reference}"
    )

    # Credit PAYE liability if > 0
    if total_paye > 0:
        JournalLine.objects.create(
            entry=entry,
            account=paye_account,
            credit=total_paye,
            description=f"PAYE liability {payroll_run.reference}"
        )

    # Credit pension liability if > 0
    if total_pension > 0:
        JournalLine.objects.create(
            entry=entry,
            account=pension_account,
            credit=total_pension,
            description=f"Pension liability {payroll_run.reference}"
        )

    payroll_run.status = 'posted'
    payroll_run.save()

    return entry

def calculate_leave_days(start_date, end_date):
    """Calculate working days between two dates (excluding weekends)."""
    days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Monday to Friday
            days += 1
        current += timedelta(days=1)
    return Decimal(str(days))


@transaction.atomic
def submit_leave_request(employee, leave_type, start_date, end_date, reason="", attachment=None):
    """Submit a leave request with automatic days calculation."""
    days = calculate_leave_days(start_date, end_date)

    # Check for overlapping requests
    existing = LeaveRequest.objects.filter(
        employee=employee,
        status__in=['pending', 'approved'],
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    if existing.exists():
        raise ValidationError("You already have a leave request for this period.")

    leave = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        reason=reason,
        attachment=attachment,
        status='pending'
    )
    return leave


@transaction.atomic
def approve_leave_request(leave, approver):
    """Approve a pending leave request."""
    if leave.status != 'pending':
        raise ValidationError("This leave request is no longer pending.")

    # Check if employee is on leave during this period
    # (additional business rules can go here)

    leave.status = 'approved'
    leave.approved_by = approver
    leave.reviewed_at = timezone.now()
    leave.save()
    return leave


@transaction.atomic
def reject_leave_request(leave, approver, reason):
    """Reject a pending leave request."""
    if leave.status != 'pending':
        raise ValidationError("This leave request is no longer pending.")
    if not reason:
        raise ValidationError("A rejection reason is required.")

    leave.status = 'rejected'
    leave.approved_by = approver
    leave.reviewed_at = timezone.now()
    leave.rejection_reason = reason
    leave.save()
    return leave


def clock_in(employee):
    """Record clock-in for an employee."""
    today = date.today()
    attendance, created = Attendance.objects.get_or_create(
        employee=employee,
        date=today,
        defaults={'clock_in': timezone.now()}
    )
    if not created and attendance.clock_in:
        raise ValidationError("You have already clocked in today.")
    if not created:
        attendance.clock_in = timezone.now()
        attendance.save()
    return attendance


def clock_out(employee):
    """Record clock-out for an employee."""
    today = date.today()
    attendance = Attendance.objects.filter(employee=employee, date=today).first()
    if not attendance or not attendance.clock_in:
        raise ValidationError("You have not clocked in today.")
    if attendance.clock_out:
        raise ValidationError("You have already clocked out today.")
    attendance.clock_out = timezone.now()
    attendance.save()
    return attendance


def get_leave_balance(employee, leave_type):
    """Calculate remaining leave days for an employee."""
    total_allowed = leave_type.days_allowed
    used = LeaveRequest.objects.filter(
        employee=employee,
        leave_type=leave_type,
        status='approved',
        end_date__gte=date.today()  # future approved leave
    ).aggregate(total=models.Sum('days'))['total'] or Decimal('0')
    return total_allowed - used