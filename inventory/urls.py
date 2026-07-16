from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category-update'),

    # Units
    path('units/', views.UnitListView.as_view(), name='unit-list'),
    path('units/add/', views.UnitCreateView.as_view(), name='unit-create'),
    path('units/<int:pk>/edit/', views.UnitUpdateView.as_view(), name='unit-update'),

    # Warehouses
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse-list'),
    path('warehouses/add/', views.WarehouseCreateView.as_view(), name='warehouse-create'),
    path('warehouses/<int:pk>/edit/', views.WarehouseUpdateView.as_view(), name='warehouse-update'),
    path('warehouses/<int:pk>/', views.WarehouseDetailView.as_view(), name='warehouse-detail'),

    # Items
    path('items/', views.ItemListView.as_view(), name='item-list'),
    path('items/add/', views.ItemCreateView.as_view(), name='item-create'),
    path('items/<int:pk>/edit/', views.ItemUpdateView.as_view(), name='item-update'),
    path('items/<int:pk>/', views.ItemDetailView.as_view(), name='item-detail'),
    path('items/<int:pk>/regenerate-qr/', views.RegenerateQRView.as_view(), name='item-regenerate-qr'),
    path('items/<int:pk>/label/', views.ItemLabelView.as_view(), name='item-label'),
    path('items/<int:pk>/label/sheet/', views.ItemLabelSheetView.as_view(), name='item-label-sheet'),
    path('scanner/', views.QRScannerView.as_view(), name='qr-scanner'),
    path('scanner/lookup/', views.QRLookupView.as_view(), name='qr-lookup'),

    # Stock
    path('stock/', views.StockListView.as_view(), name='stock-list'),
    path('movements/', views.StockMovementListView.as_view(), name='movement-list'),
    
    # Stock Operations
    path('stock/receive/', views.StockReceiveView.as_view(), name='stock-receive'),
    path('stock/issue/', views.StockIssueView.as_view(), name='stock-issue'),
    path('stock/transfer/', views.StockTransferView.as_view(), name='stock-transfer'),
    path('stock/adjust/', views.StockAdjustView.as_view(), name='stock-adjust'),
]