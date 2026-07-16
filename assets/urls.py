from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [

    # Categories
    path('categories/', views.AssetCategoryListView.as_view(), name='category-list'),
    path('categories/add/', views.AssetCategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', views.AssetCategoryUpdateView.as_view(), name='category-update'),

    # Assets
    path('', views.AssetListView.as_view(), name='asset-list'),
    path('add/', views.AssetCreateView.as_view(), name='asset-create'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='asset-detail'),
    path('<int:pk>/edit/', views.AssetUpdateView.as_view(), name='asset-update'),

    # Assignment & Return
    path('<int:pk>/assign/', views.AssetAssignView.as_view(), name='asset-assign'),
    path('<int:pk>/return/', views.AssetReturnView.as_view(), name='asset-return'),

    # Maintenance
    path('maintenance/', views.MaintenanceListView.as_view(), name='maintenance-list'),
    path('<int:asset_pk>/maintenance/add/', views.MaintenanceCreateView.as_view(), name='maintenance-create'),
    path('maintenance/<int:pk>/edit/', views.MaintenanceUpdateView.as_view(), name='maintenance-update'),
]