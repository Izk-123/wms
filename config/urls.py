from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('reports.urls')),   
    path('inventory/', include('inventory.urls')),
    path('procurement/', include('procurement.urls')),
    path('operations/', include('operations.urls')),
    path('assets/', include('assets.urls')),
    path('accounts/', include('accounts.urls')),
    path('notifications/', include('notifications.urls')),
    path('sales/', include('sales.urls')),
    path('finance/', include('finance.urls')),
    path('settings/', include('company_settings.urls')),
    path('hr/', include('hr.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
