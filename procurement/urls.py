from django.urls import path
from . import views

app_name = 'procurement'

urlpatterns = [

    # Suppliers
    path('suppliers/', views.SupplierListView.as_view(), name='supplier-list'),
    path('suppliers/add/', views.SupplierCreateView.as_view(), name='supplier-create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier-update'),

    # Purchase Requests
    path('requests/', views.PurchaseRequestListView.as_view(), name='pr-list'),
    path('requests/add/', views.PurchaseRequestCreateView.as_view(), name='pr-create'),
    path('requests/<int:pk>/', views.PurchaseRequestDetailView.as_view(), name='pr-detail'),
    path('requests/<int:pk>/<str:action>/', views.PurchaseRequestActionView.as_view(), name='pr-action'),

    # Purchase Orders
    path('orders/', views.PurchaseOrderListView.as_view(), name='po-list'),
    path('orders/add/', views.PurchaseOrderCreateView.as_view(), name='po-create'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='po-detail'),
    path('orders/<int:pk>/mark-sent/', views.PurchaseOrderMarkSentView.as_view(), name='po-mark-sent'),

    # Goods Receipts
    path('grn/', views.GoodsReceiptListView.as_view(), name='grn-list'),
    path('grn/create/<int:po_pk>/', views.GoodsReceiptCreateView.as_view(), name='grn-create'),
    path('grn/<int:pk>/', views.GoodsReceiptDetailView.as_view(), name='grn-detail'),
    path('grn/<int:pk>/confirm/', views.GoodsReceiptConfirmView.as_view(), name='grn-confirm'),
]