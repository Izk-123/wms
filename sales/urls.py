# sales/urls.py
from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer-update'),

    # Sales Orders
    path('orders/', views.SalesOrderListView.as_view(), name='order-list'),
    path('orders/add/', views.SalesOrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', views.SalesOrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:pk>/edit/', views.SalesOrderUpdateView.as_view(), name='order-update'),
    path('orders/<int:pk>/approve-discount/', views.ApproveDiscountView.as_view(), name='approve-discount'),

    # ─── NEW: Ready to Invoice ───────────────────────
    path('ready-to-invoice/', views.ReadyToInvoiceListView.as_view(), name='ready-to-invoice'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/add/', views.InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/add/order/<int:order_pk>/', views.InvoiceCreateView.as_view(), name='invoice-create-from-order'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/print/', views.InvoicePrintView.as_view(), name='invoice-print'),

    # Payments
    path('invoices/<int:invoice_pk>/payment/', views.PaymentCreateView.as_view(), name='payment-create'),
]