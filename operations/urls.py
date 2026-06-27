from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [

    # Projects
    path('projects/', views.ProjectListView.as_view(), name='project-list'),
    path('projects/add/', views.ProjectCreateView.as_view(), name='project-create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project-update'),

    # Material Requests
    path('requests/', views.MaterialRequestListView.as_view(), name='mr-list'),
    path('requests/add/', views.MaterialRequestCreateView.as_view(), name='mr-create'),
    path('requests/<int:pk>/', views.MaterialRequestDetailView.as_view(), name='mr-detail'),
    path('requests/<int:pk>/<str:action>/', views.MaterialRequestActionView.as_view(), name='mr-action'),

    # Material Returns
    path('returns/<int:mr_pk>/', views.MaterialReturnCreateView.as_view(), name='return-create'),
]