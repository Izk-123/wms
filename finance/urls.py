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
]