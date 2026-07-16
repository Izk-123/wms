from django.urls import path
from . import views

app_name = 'company_settings'

urlpatterns = [
    path('approvals/', views.ApprovalRequestListView.as_view(), name='approval-list'),
    path('approvals/<int:pk>/', views.ApprovalRequestDetailView.as_view(), name='approval-detail'),
    path('approvals/<int:pk>/action/', views.ApprovalActionView.as_view(), name='approval-action'),
]