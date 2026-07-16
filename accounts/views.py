# accounts/views.py
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, View, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import models
from django.utils import timezone
from django.http import JsonResponse

from core.mixins import WMSPermissionMixin
from .models import User, Role, LoginHistory, UserActivity, UserTutorial
from .forms import (
    UserCreateForm, UserUpdateForm, ProfileUpdateForm,
    ForcePasswordChangeForm, AdminPasswordResetForm, RoleForm
)


# ─── Helper: Log Activity ──────────────────────────────────────
def log_activity(user, action, module, request=None):
    """
    Record a user action with optional request metadata (IP, user agent).
    """
    ip = None
    ua = ''
    if request:
        # Handle proxies
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = (
            x_forwarded.split(',')[0].strip()
            if x_forwarded
            else request.META.get('REMOTE_ADDR')
        )
        ua = request.META.get('HTTP_USER_AGENT', '')

    UserActivity.objects.create(
        user=user,
        action=action,
        module=module,
        ip_address=ip,
        user_agent=ua,
    )


# ─── Authentication Views ──────────────────────────────────────

class CustomLoginView(BaseLoginView):
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()

        # Record login history
        ip = self.request.META.get('REMOTE_ADDR', '')
        ua = self.request.META.get('HTTP_USER_AGENT', '')
        LoginHistory.objects.create(
            user=user,
            ip_address=ip or '127.0.0.1',
            user_agent=ua,
        )

        login(self.request, user)

        # Force password change on first login
        if user.must_change_password:
            return redirect('accounts:force-password-change')

        return redirect('reports:dashboard')


class CustomLogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('accounts:login')


class ForcePasswordChangeView(LoginRequiredMixin, FormView):
    template_name = 'accounts/force_password_change.html'
    form_class = ForcePasswordChangeForm

    def dispatch(self, request, *args, **kwargs):
        # If password doesn't need changing, redirect away
        if request.user.is_authenticated and not request.user.must_change_password:
            return redirect('reports:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data['new_password1'])
        user.must_change_password = False
        user.is_first_login = False
        user.save()

        update_session_auth_hash(self.request, user)

        log_activity(
            user,
            "Changed password on first login",
            "Accounts",
            request=self.request
        )
        messages.success(self.request, "Password changed successfully. Welcome!")
        return redirect('reports:dashboard')


# ─── User Management Views ─────────────────────────────────────

class UserListView(WMSPermissionMixin, ListView):
    permission_required = 'accounts.manage_users'
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('role').order_by(
            'last_name', 'first_name'
        )
        q = self.request.GET.get('q')
        role = self.request.GET.get('role')
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(employee_number__icontains=q)
            )
        if role:
            qs = qs.filter(role_id=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['roles'] = Role.objects.all()
        ctx['selected_role'] = self.request.GET.get('role', '')
        return ctx


class UserCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'accounts.manage_users'
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user-list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Auto‑assign to matching Django Group
        if self.object.role:
            try:
                group = Group.objects.get(name=self.object.role.name)
                self.object.groups.add(group)
            except Group.DoesNotExist:
                pass

        log_activity(
            self.request.user,
            f"Created user: {self.object.get_full_name() or self.object.username}",
            "Accounts",
            request=self.request
        )
        messages.success(
            self.request,
            f"User {self.object.get_full_name()} created successfully. "
            "They will be prompted to change password on first login."
        )
        return response


class UserUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'accounts.manage_users'
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user-list')

    def form_valid(self, form):
        response = super().form_valid(form)

        # Re‑sync group – clear old groups and assign new one
        self.object.groups.clear()
        if self.object.role:
            try:
                group = Group.objects.get(name=self.object.role.name)
                self.object.groups.add(group)
            except Group.DoesNotExist:
                pass

        log_activity(
            self.request.user,
            f"Updated user: {self.object.get_full_name() or self.object.username}",
            "Accounts",
            request=self.request
        )
        messages.success(self.request, "User updated successfully.")
        return response


class UserDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'accounts.manage_users'
    model = User
    template_name = 'accounts/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_activity'] = UserActivity.objects.filter(
            user=self.object
        ).order_by('-created_at')[:20]
        ctx['login_history'] = LoginHistory.objects.filter(
            user=self.object
        ).order_by('-login_time')[:10]
        return ctx


class UserDeactivateView(WMSPermissionMixin, View):
    permission_required = 'accounts.manage_users'

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect('accounts:user-list')

        user.is_active = not user.is_active
        user.save()

        action = "Activated" if user.is_active else "Deactivated"
        log_activity(
            request.user,
            f"{action} user: {user.get_full_name() or user.username}",
            "Accounts",
            request=request
        )
        messages.success(request, f"User {action.lower()} successfully.")
        return redirect('accounts:user-list')


class AdminPasswordResetView(WMSPermissionMixin, FormView):
    permission_required = 'accounts.manage_users'
    template_name = 'accounts/admin_password_reset.html'
    form_class = AdminPasswordResetForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['profile_user'] = get_object_or_404(User, pk=self.kwargs['pk'])
        return ctx

    def form_valid(self, form):
        user = get_object_or_404(User, pk=self.kwargs['pk'])
        user.set_password(form.cleaned_data['new_password'])
        user.must_change_password = True
        user.save()

        log_activity(
            self.request.user,
            f"Reset password for: {user.get_full_name() or user.username}",
            "Accounts",
            request=self.request
        )
        messages.success(
            self.request,
            f"Password reset for {user.get_full_name()}. "
            "They will be prompted to change it on next login."
        )
        return redirect('accounts:user-detail', pk=user.pk)


# ─── Profile Views ────────────────────────────────────────────

class ProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_activity'] = UserActivity.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:10]
        return ctx


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile_update.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


# ─── Role Views ────────────────────────────────────────────────

class RoleListView(WMSPermissionMixin, ListView):
    permission_required = 'accounts.manage_roles'
    model = Role
    template_name = 'accounts/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return super().get_queryset().annotate(
            user_count=models.Count('users')
        )


class RoleCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'accounts.manage_roles'
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role-list')

    def form_valid(self, form):
        messages.success(self.request, "Role created successfully.")
        return super().form_valid(form)


class RoleUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'accounts.manage_roles'
    model = Role
    form_class = RoleForm
    template_name = 'accounts/role_form.html'
    success_url = reverse_lazy('accounts:role-list')

    def form_valid(self, form):
        messages.success(self.request, "Role updated successfully.")
        return super().form_valid(form)


# ─── Tutorial Views ────────────────────────────────────────────

class MarkWelcomeSeenView(LoginRequiredMixin, View):
    def post(self, request):
        tutorial, _ = UserTutorial.objects.get_or_create(user=request.user)
        tutorial.welcome_seen = True
        tutorial.save()
        return JsonResponse({'status': 'ok'})


class MarkTourCompleteView(LoginRequiredMixin, View):
    def post(self, request):
        tutorial, _ = UserTutorial.objects.get_or_create(user=request.user)
        tutorial.tour_completed = True
        tutorial.tour_completed_at = timezone.now()

        import json
        try:
            body = json.loads(request.body)
            tutorial.tour_step_reached = body.get('step', 0)
        except Exception:
            pass

        tutorial.save()
        return JsonResponse({'status': 'ok'})


class ReplayTourView(LoginRequiredMixin, View):
    def post(self, request):
        tutorial, _ = UserTutorial.objects.get_or_create(user=request.user)
        tutorial.tour_completed = False
        tutorial.welcome_seen = False
        tutorial.tour_step_reached = 0
        tutorial.tour_completed_at = None
        tutorial.save()
        messages.success(request, "Tutorial reset. Refresh the page to start.")
        return redirect('accounts:profile')