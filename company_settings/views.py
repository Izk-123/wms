from django.views.generic import DetailView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from core.mixins import WMSPermissionMixin
from .models import ApprovalRequest
from .services import approve_request, reject_request, user_can_approve

class ApprovalRequestListView(LoginRequiredMixin, ListView):
    model = ApprovalRequest
    template_name = 'company_settings/approval_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(status='pending')
        # Show only requests where the user can approve
        # (or show all to admins)
        if not self.request.user.has_perm('company_settings.manage_system_settings'):
            # Filter by user's role
            user_roles = [self.request.user.role] if self.request.user.role else []
            qs = qs.filter(approvalrule__required_role__in=user_roles)
        return qs

class ApprovalRequestDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'company_settings.view_approvalrequest'
    model = ApprovalRequest
    template_name = 'company_settings/approval_detail.html'
    context_object_name = 'request'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['can_approve'] = user_can_approve(
            self.request.user,
            self.object.action,
            self.object.amount
        )
        return ctx

class ApprovalActionView(WMSPermissionMixin, View):
    permission_required = 'company_settings.approve_approvalrequest'

    def post(self, request, pk):
        approval_request = get_object_or_404(ApprovalRequest, pk=pk)
        action = request.POST.get('action')

        if approval_request.status != 'pending':
            messages.error(request, "This request is no longer pending.")
            return redirect('company_settings:approval-list')

        try:
            if action == 'approve':
                approve_request(approval_request, request.user)
                messages.success(request, "Request approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_request(approval_request, request.user, reason)
                messages.warning(request, "Request rejected.")
            else:
                messages.error(request, "Invalid action.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('company_settings:approval-list')