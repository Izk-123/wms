from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('accounts/', views.AccountListView.as_view(), name='account-list'),
    path('accounts/add/', views.AccountCreateView.as_view(), name='account-create'),
    path('accounts/<int:pk>/edit/', views.AccountUpdateView.as_view(), name='account-update'),
    path('journal/', views.JournalEntryListView.as_view(), name='journal-list'),
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense-create'),
    path('expenses/<int:pk>/', views.ExpenseDetailView.as_view(), name='expense-detail'),
    path('expenses/<int:pk>/approve/', views.ExpenseApproveView.as_view(), name='expense-approve'),
    path('expenses/<int:pk>/pay/', views.ExpensePayView.as_view(), name='expense-pay'),

    # ─── Cashier Workspace ──────────────────────────────
    path('cashier/', views.CashierDashboardView.as_view(), name='cashier-dashboard'),
    path('cashier/open-drawer/', views.OpenDrawerView.as_view(), name='open-drawer'),
    path('cashier/close-drawer/', views.CloseDrawerView.as_view(), name='close-drawer'),

    # ─── Accounts Payable ───────────────────────────────
    path('supplier-bills/', views.SupplierBillListView.as_view(), name='supplier-bill-list'),
    path('supplier-bills/add/', views.SupplierBillCreateView.as_view(), name='supplier-bill-create'),
    path('supplier-bills/<int:pk>/', views.SupplierBillDetailView.as_view(), name='supplier-bill-detail'),
    path('supplier-bills/<int:pk>/approve/', views.SupplierBillApproveView.as_view(), name='supplier-bill-approve'),
    path('supplier-bills/<int:pk>/pay/', views.SupplierBillPayView.as_view(), name='supplier-bill-pay'),
    
    # ─── Bank Accounts & Reconciliation ────────────────────
    path('bank-accounts/', views.BankAccountListView.as_view(), name='bank-account-list'),
    path('bank-accounts/<int:account_id>/reconcile/', views.BankReconciliationView.as_view(), name='bank-reconciliation'),
    path('bank-accounts/import-statement/', views.ImportBankStatementView.as_view(), name='import-bank-statement'),

    # ─── Budgets ────────────────────────────────────────────
    path('budgets/', views.BudgetListView.as_view(), name='budget-list'),
    path('budgets/add/', views.BudgetCreateView.as_view(), name='budget-create'),
    path('budgets/<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='budget-update'),
    path('budgets/vs-actual/', views.BudgetVsActualView.as_view(), name='budget-vs-actual'),

    # ─── Fiscal Periods ──────────────────────────────────────
    path('periods/', views.FiscalPeriodListView.as_view(), name='period-list'),
    path('periods/add/', views.FiscalPeriodCreateView.as_view(), name='period-create'),
    path('periods/<int:pk>/close/', views.ClosePeriodView.as_view(), name='period-close'),

    # ─── Audit Log ───────────────────────────────────────────
    path('audit-log/', views.AuditLogView.as_view(), name='audit-log'),
]
