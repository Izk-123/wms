from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RelatedDropdownFilter
from .models import (
    Department, Position, Employee, EmploymentHistory,
    LeaveType, LeaveRequest, Attendance, EmployeeDocument
)


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ('code', 'name', 'manager', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Position)
class PositionAdmin(ModelAdmin):
    list_display = ('name', 'department', 'is_active')
    list_filter = ('is_active', ('department', RelatedDropdownFilter))
    search_fields = ('name',)


@admin.register(Employee)
class EmployeeAdmin(ModelAdmin):
    list_display = ('employee_id', 'full_name', 'position', 'department', 'employment_status', 'is_active')
    list_filter = ('employment_status', 'employment_type', 'department', 'is_active')
    search_fields = ('employee_id', 'first_name', 'last_name', 'company_email')
    readonly_fields = ('employee_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'user', 'first_name', 'middle_name', 'last_name', 'gender', 'date_of_birth', 'national_id')
        }),
        ('Contact', {
            'fields': ('company_email', 'personal_email', 'phone', 'mobile', 'physical_address')
        }),
        ('Employment', {
            'fields': ('department', 'position', 'branch', 'supervisor', 'employment_status', 'employment_type', 'date_joined', 'date_left')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')
        }),
        ('Additional', {
            'fields': ('profile_photo', 'notes', 'is_active')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(LeaveType)
class LeaveTypeAdmin(ModelAdmin):
    list_display = ('name', 'code', 'days_allowed', 'is_active')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'days', 'status')
    list_filter = ('status', 'leave_type', 'start_date')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ('employee', 'date', 'clock_in', 'clock_out', 'is_late', 'is_overtime')
    list_filter = ('date', 'is_late')


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(ModelAdmin):
    list_display = ('employee', 'title', 'document_type', 'expiry_date', 'uploaded_at')
    list_filter = ('document_type',)
    
from unfold.admin import ModelAdmin
from .models import SalaryStructure, SalaryComponent, EmployeeSalary, PayrollRun, PayrollItem, Payslip

@admin.register(SalaryStructure)
class SalaryStructureAdmin(ModelAdmin):
    list_display = ('name', 'is_active')

@admin.register(SalaryComponent)
class SalaryComponentAdmin(ModelAdmin):
    list_display = ('code', 'name', 'structure', 'is_deduction', 'calculation_type', 'amount')

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(ModelAdmin):
    list_display = ('employee', 'structure', 'effective_date')

@admin.register(PayrollRun)
class PayrollRunAdmin(ModelAdmin):
    list_display = ('reference', 'period_start', 'period_end', 'status', 'run_date')
    list_filter = ('status', 'run_date')

@admin.register(PayrollItem)
class PayrollItemAdmin(ModelAdmin):
    list_display = ('payroll', 'employee', 'gross_pay', 'net_pay')

@admin.register(Payslip)
class PayslipAdmin(ModelAdmin):
    list_display = ('payroll_item', 'generated_at')