from django.http import HttpResponse
from django.views.generic import ListView, CreateView, TemplateView, UpdateView, DetailView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, Count, Sum, F, Value
from django.db.models.functions import Concat
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity
from .models import Department, PayrollRun, Payslip, Position, Employee, LeaveRequest, Attendance, LeaveType, EmployeeDocument
from .forms import (
    DepartmentForm, PositionForm, EmployeeForm,
    LeaveRequestForm, LeaveRequestApproveForm,
)
from .services import (
    get_leave_balance, post_payroll_to_finance, process_payroll, submit_leave_request, approve_leave_request,
    reject_leave_request, clock_in, clock_out
)


class MyProfileView(LoginRequiredMixin, DetailView):
    template_name = 'hr/my_profile.html'
    context_object_name = 'employee'

    def get_object(self):
        try:
            return self.request.user.employee_profile
        except Employee.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['leave_balance'] = {}
        if self.object:
            for lt in LeaveType.objects.filter(is_active=True):
                ctx['leave_balance'][lt.code] = get_leave_balance(self.object, lt)
        return ctx

# ─── Dashboard ──────────────────────────────────────────────
class HRDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'hr/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        ctx.update({
            'total_employees': Employee.objects.filter(is_active=True).count(),
            'departments': Department.objects.filter(is_active=True).count(),
            'pending_leave': LeaveRequest.objects.filter(status='pending').count(),
            'today_attendance': Attendance.objects.filter(date=today).count(),
            'on_leave_today': LeaveRequest.objects.filter(
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).count(),
            'recent_leave': LeaveRequest.objects.select_related(
                'employee', 'leave_type'
            ).order_by('-submitted_at')[:10],
            'recent_employees': Employee.objects.order_by('-created_at')[:10],
        })
        return ctx


# ─── Department Views ─────────────────────────────────────
class DepartmentListView(WMSPermissionMixin, ListView):
    permission_required = 'hr.view_department'
    model = Department
    template_name = 'hr/department_list.html'
    context_object_name = 'departments'

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('positions')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class DepartmentCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'hr.add_department'
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department_form.html'
    success_url = reverse_lazy('hr:department-list')


class DepartmentUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'hr.change_department'
    model = Department
    form_class = DepartmentForm
    template_name = 'hr/department_form.html'
    success_url = reverse_lazy('hr:department-list')


# ─── Employee Views ──────────────────────────────────────
class EmployeeListView(WMSPermissionMixin, ListView):
    permission_required = 'hr.view_employee'
    model = Employee
    template_name = 'hr/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('department', 'position', 'user')
        q = self.request.GET.get('q')
        department = self.request.GET.get('department')
        status = self.request.GET.get('status')

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(employee_id__icontains=q) |
                Q(company_email__icontains=q)
            )
        if department:
            qs = qs.filter(department_id=department)
        if status:
            qs = qs.filter(employment_status=status)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['departments'] = Department.objects.filter(is_active=True)
        ctx['statuses'] = Employee.EMPLOYMENT_STATUS_CHOICES
        ctx['selected_department'] = self.request.GET.get('department', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class EmployeeCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'hr.add_employee'
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(
            self.request.user,
            f"Created employee: {self.object.full_name} ({self.object.employee_id})",
            "HR",
            request=self.request
        )
        messages.success(self.request, f"Employee {self.object.full_name} created.")
        return response


class EmployeeUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'hr.change_employee'
    model = Employee
    form_class = EmployeeForm
    template_name = 'hr/employee_form.html'
    success_url = reverse_lazy('hr:employee-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        log_activity(
            self.request.user,
            f"Updated employee: {self.object.full_name} ({self.object.employee_id})",
            "HR",
            request=self.request
        )
        messages.success(self.request, f"Employee {self.object.full_name} updated.")
        return response


class EmployeeDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'hr.view_employee'
    model = Employee
    template_name = 'hr/employee_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['leave_requests'] = self.object.leave_requests.order_by('-submitted_at')[:10]
        ctx['attendance'] = self.object.attendance.order_by('-date')[:10]
        ctx['documents'] = self.object.documents.all()
        return ctx


# ─── Leave Views ──────────────────────────────────────────
class LeaveRequestListView(WMSPermissionMixin, ListView):
    permission_required = 'hr.view_leaverequest'
    model = LeaveRequest
    template_name = 'hr/leave_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('employee', 'leave_type', 'approved_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = LeaveRequest.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class LeaveRequestCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'hr.add_leaverequest'
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'hr/leave_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['employee_list'] = Employee.objects.filter(is_active=True)
        return ctx

    def form_valid(self, form):
        try:
            employee = form.cleaned_data['employee']
            leave_type = form.cleaned_data['leave_type']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            reason = form.cleaned_data['reason']
            attachment = form.cleaned_data.get('attachment')

            leave = submit_leave_request(employee, leave_type, start_date, end_date, reason, attachment)

            log_activity(
                self.request.user,
                f"Submitted leave request for {employee.full_name} ({leave.reference})",
                "HR",
                request=self.request
            )
            messages.success(self.request, "Leave request submitted.")
            return redirect('hr:leave-detail', pk=leave.pk)
        except ValidationError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class LeaveRequestDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'hr.view_leaverequest'
    model = LeaveRequest
    template_name = 'hr/leave_detail.html'
    context_object_name = 'leave'


class LeaveRequestApproveView(WMSPermissionMixin, View):
    permission_required = 'hr.manage_leave'

    def post(self, request, pk):
        leave = get_object_or_404(LeaveRequest, pk=pk)
        action = request.POST.get('action')

        try:
            if action == 'approve':
                approve_leave_request(leave, request.user)
                log_activity(
                    request.user,
                    f"Approved leave request for {leave.employee.full_name}",
                    "HR",
                    request=request
                )
                messages.success(request, "Leave request approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_leave_request(leave, request.user, reason)
                log_activity(
                    request.user,
                    f"Rejected leave request for {leave.employee.full_name}",
                    "HR",
                    request=request
                )
                messages.warning(request, "Leave request rejected.")
            else:
                messages.error(request, "Invalid action.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('hr:leave-detail', pk=pk)


# ─── Attendance Views ─────────────────────────────────────
class AttendanceListView(WMSPermissionMixin, ListView):
    permission_required = 'hr.view_attendance'
    model = Attendance
    template_name = 'hr/attendance_list.html'
    context_object_name = 'attendance_records'
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset().select_related('employee')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class AttendanceClockView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            employee = request.user.employee_profile
            action = request.POST.get('action')

            if action == 'clock_in':
                attendance = clock_in(employee)
                messages.success(request, f"Clocked in at {attendance.clock_in.strftime('%H:%M')}")
            elif action == 'clock_out':
                attendance = clock_out(employee)
                messages.success(request, f"Clocked out at {attendance.clock_out.strftime('%H:%M')}")
            else:
                messages.error(request, "Invalid action.")
        except (AttributeError, ValidationError) as e:
            messages.error(request, str(e))

        return redirect('hr:attendance-list')
    
# ─── Payroll Views ────────────────────────────────────────────

class PayrollRunListView(WMSPermissionMixin, ListView):
    permission_required = 'hr.view_payrollrun'
    model = PayrollRun
    template_name = 'hr/payroll_list.html'
    context_object_name = 'payrolls'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PayrollRun.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class PayrollRunCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'hr.add_payrollrun'
    model = PayrollRun
    fields = ['period_start', 'period_end', 'notes']
    template_name = 'hr/payroll_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.info(self.request, "Payroll created as draft. Process it to calculate employees.")
        return redirect('hr:payroll-detail', pk=self.object.pk)


class PayrollRunDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'hr.view_payrollrun'
    model = PayrollRun
    template_name = 'hr/payroll_detail.html'
    context_object_name = 'payroll'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('employee', 'payslip')
        return ctx


class PayrollRunProcessView(WMSPermissionMixin, View):
    permission_required = 'hr.process_payrollrun'

    def post(self, request, pk):
        payroll = get_object_or_404(PayrollRun, pk=pk)
        try:
            process_payroll(payroll)
            log_activity(
                request.user,
                f"Processed payroll {payroll.reference}",
                "HR",
                request=request
            )
            messages.success(request, f"Payroll {payroll.reference} processed.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('hr:payroll-detail', pk=pk)


class PayrollRunPostView(WMSPermissionMixin, View):
    permission_required = 'hr.post_payrollrun'

    def post(self, request, pk):
        payroll = get_object_or_404(PayrollRun, pk=pk)
        try:
            entry = post_payroll_to_finance(payroll)
            log_activity(
                request.user,
                f"Posted payroll {payroll.reference} to Finance (Journal #{entry.pk})",
                "HR",
                request=request
            )
            messages.success(request, f"Payroll {payroll.reference} posted to Finance.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('hr:payroll-detail', pk=pk)


class PayslipDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk):
        payslip = get_object_or_404(Payslip, pk=pk)
        # Check permission: employee can view own, or HR staff
        if request.user != payslip.payroll_item.employee.user and not request.user.has_perm('hr.view_payslip'):
            messages.error(request, "You do not have permission to view this payslip.")
            return redirect('hr:payroll-list')
        response = HttpResponse(payslip.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{payslip.pdf_file.name}"'
        return response