from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats/', views.DashboardStatsPartialView.as_view(), name='dashboard-stats'),

    # Reports
    path('inventory/', views.InventoryReportView.as_view(), name='inventory'),
    path('movements/', views.StockMovementReportView.as_view(), name='movements'),
    path('projects/', views.ProjectConsumptionReportView.as_view(), name='projects'),

    # Excel exports
    path('export/inventory/excel/', views.ExportInventoryExcelView.as_view(), name='export-inventory-excel'),
    path('export/movements/excel/', views.ExportMovementsExcelView.as_view(), name='export-movements-excel'),

    # PDF exports
    path('export/inventory/pdf/', views.ExportInventoryPDFView.as_view(), name='export-inventory-pdf'),
    
    # Global Search
    path('search/', views.GlobalSearchView.as_view(), name='search'),
]