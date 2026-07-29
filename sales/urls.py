# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer-update'),

    # Quotations
    path('quotations/', views.QuotationListView.as_view(), name='quotation-list'),
    path('quotations/add/', views.QuotationCreateView.as_view(), name='quotation-create'),
    path('quotations/<int:pk>/', views.QuotationDetailView.as_view(), name='quotation-detail'),
    path('quotations/<int:pk>/edit/', views.QuotationUpdateView.as_view(), name='quotation-update'),
    path('quotations/<int:pk>/accept/', views.QuotationAcceptView.as_view(), name='quotation-accept'),
    path('quotations/<int:pk>/print/', views.QuotationPDFView.as_view(), name='quotation-print'),

    # Sales Orders
    path('orders/', views.SalesOrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', views.SalesOrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/print/', views.SalesOrderPDFView.as_view(), name='order-print'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/print/', views.InvoicePDFView.as_view(), name='invoice-print'),
    path('invoices/<int:pk>/email/', views.InvoiceEmailView.as_view(), name='invoice-email'),

    # Payments
    path('invoices/<int:invoice_pk>/payment/', views.PaymentCreateView.as_view(), name='payment-create'),
]
