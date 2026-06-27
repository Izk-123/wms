from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [

    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('change-password/', views.ForcePasswordChangeView.as_view(), name='force-password-change'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile-update'),

    # User Management (Admin only)
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/add/', views.UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user-update'),
    path('users/<int:pk>/deactivate/', views.UserDeactivateView.as_view(), name='user-deactivate'),
    path('users/<int:pk>/reset-password/', views.AdminPasswordResetView.as_view(), name='user-reset-password'),

    # Roles (Admin only)
    path('roles/', views.RoleListView.as_view(), name='role-list'),
    path('roles/add/', views.RoleCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/edit/', views.RoleUpdateView.as_view(), name='role-update'),
    
    # Tutorial
    path('tutorial/welcome-seen/', views.MarkWelcomeSeenView.as_view(), name='tutorial-welcome-seen'),
    path('tutorial/complete/', views.MarkTourCompleteView.as_view(), name='tutorial-complete'),
    path('tutorial/replay/', views.ReplayTourView.as_view(), name='tutorial-replay'),
    
    # Forgot Password
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/email/password_reset_email.html',
            subject_template_name='accounts/email/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/',
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/reset/done/',
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]