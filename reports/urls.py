from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [

    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/stats/', views.DashboardStatsPartialView.as_view(), name='dashboard-stats'),

    # Inventory Reports
    path('inventory/', views.InventoryReportView.as_view(), name='inventory'),
    path('movements/', views.StockMovementReportView.as_view(), name='movements'),
    path('projects/', views.ProjectConsumptionReportView.as_view(), name='projects'),

    # ─── NEW FINANCE REPORTS ──────────────────────────
    path('finance/income-statement/', views.IncomeStatementView.as_view(), name='income-statement'),
    path('finance/cash-flow/', views.CashFlowView.as_view(), name='cash-flow'),
    path('finance/balance-sheet/', views.BalanceSheetView.as_view(), name='balance-sheet'),
    
    # Finance Exports
    path('export/income-statement/excel/', views.ExportIncomeStatementExcelView.as_view(), name='export-income-statement-excel'),
    path('export/income-statement/pdf/', views.ExportIncomeStatementPDFView.as_view(), name='export-income-statement-pdf'),
    path('export/cash-flow/excel/', views.ExportCashFlowExcelView.as_view(), name='export-cash-flow-excel'),
    path('export/cash-flow/pdf/', views.ExportCashFlowPDFView.as_view(), name='export-cash-flow-pdf'),
    path('export/balance-sheet/excel/', views.ExportBalanceSheetExcelView.as_view(), name='export-balance-sheet-excel'),
    path('export/balance-sheet/pdf/', views.ExportBalanceSheetPDFView.as_view(), name='export-balance-sheet-pdf'),

    # Excel exports
    path('export/inventory/excel/', views.ExportInventoryExcelView.as_view(), name='export-inventory-excel'),
    path('export/movements/excel/', views.ExportMovementsExcelView.as_view(), name='export-movements-excel'),

    # PDF exports
    path('export/inventory/pdf/', views.ExportInventoryPDFView.as_view(), name='export-inventory-pdf'),

    # Global Search
    path('search/', views.GlobalSearchView.as_view(), name='search'),
]