from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Dashboard
    path('', views.HRDashboardView.as_view(), name='dashboard'),
    
    path('my-profile/', views.MyProfileView.as_view(), name='my-profile'),

    # Departments
    path('departments/', views.DepartmentListView.as_view(), name='department-list'),
    path('departments/add/', views.DepartmentCreateView.as_view(), name='department-create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department-update'),

    # Employees
    path('employees/', views.EmployeeListView.as_view(), name='employee-list'),
    path('employees/add/', views.EmployeeCreateView.as_view(), name='employee-create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee-update'),

    # Leave
    path('leave/', views.LeaveRequestListView.as_view(), name='leave-list'),
    path('leave/add/', views.LeaveRequestCreateView.as_view(), name='leave-create'),
    path('leave/<int:pk>/', views.LeaveRequestDetailView.as_view(), name='leave-detail'),
    path('leave/<int:pk>/action/', views.LeaveRequestApproveView.as_view(), name='leave-action'),

    # Attendance
    path('attendance/', views.AttendanceListView.as_view(), name='attendance-list'),
    path('attendance/clock/', views.AttendanceClockView.as_view(), name='attendance-clock'),
    
       # Payroll
    path('payroll/', views.PayrollRunListView.as_view(), name='payroll-list'),
    path('payroll/add/', views.PayrollRunCreateView.as_view(), name='payroll-create'),
    path('payroll/<int:pk>/', views.PayrollRunDetailView.as_view(), name='payroll-detail'),
    path('payroll/<int:pk>/process/', views.PayrollRunProcessView.as_view(), name='payroll-process'),
    path('payroll/<int:pk>/post/', views.PayrollRunPostView.as_view(), name='payroll-post'),
    path('payslip/<int:pk>/download/', views.PayslipDownloadView.as_view(), name='payslip-download'),
]