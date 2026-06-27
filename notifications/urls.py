from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('count/', views.NotificationCountView.as_view(), name='count'),
    path('dropdown/', views.NotificationDropdownView.as_view(), name='dropdown'),
    path('<int:pk>/read/', views.MarkReadView.as_view(), name='mark-read'),
    path('read-all/', views.MarkAllReadView.as_view(), name='mark-all-read'),
]