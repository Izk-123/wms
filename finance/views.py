from django.views.generic import ListView, CreateView, DetailView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from company_settings.models import ApprovalRequest
from company_settings.services import (
    approve_request, create_approval_request, get_approval_required,
    reject_request, user_can_approve
)
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity
from .models import Account, JournalEntry, Expense
from .forms import AccountForm, ExpenseForm
from .services import create_expense_journal_entry


# ─── Account Views ──────────────────────────────────────

class AccountListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_account'
    model = Account
    template_name = 'finance/account_list.html'
    context_object_name = 'accounts'


class AccountCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'finance.add_account'
    model = Account
    form_class = AccountForm
    template_name = 'finance/account_form.html'
    success_url = reverse_lazy('finance:account-list')


class AccountUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'finance.change_account'
    model = Account
    form_class = AccountForm
    template_name = 'finance/account_form.html'
    success_url = reverse_lazy('finance:account-list')


# ─── Journal Entry Views (read‑only) ────────────────────

class JournalEntryListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_journalentry'
    model = JournalEntry
    template_name = 'finance/journal_entry_list.html'
    context_object_name = 'entries'
    paginate_by = 30
    ordering = ['-entry_date']


# ─── Expense Views ──────────────────────────────────────

class ExpenseListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_expense'
    model = Expense
    template_name = 'finance/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('created_by', 'approved_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Expense.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class ExpenseCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'finance.add_expense'
    model = Expense
    form_class = ExpenseForm
    template_name = 'finance/expense_form.html'

    def form_valid(self, form):
        expense = form.save(commit=False)
        expense.created_by = self.request.user
        amount = expense.amount
        required_role = get_approval_required('expense', amount)
        if required_role and not user_can_approve(self.request.user, 'expense', amount):
            expense.status = 'pending_approval'
            expense.save()
            create_approval_request(
                user=self.request.user,
                action='expense',
                amount=amount,
                reference=expense.reference,
                notes=expense.description,
                content_object=expense
            )
            messages.info(self.request, "Expense submitted for approval.")
            return redirect('finance:expense-list')
        expense.status = 'approved'
        expense.save()
        log_activity(
            self.request.user,
            f"Created expense {expense.reference}",
            "Finance",
            request=self.request
        )
        messages.success(self.request, "Expense recorded.")
        return redirect('finance:expense-detail', pk=expense.pk)


class ExpenseDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'finance.view_expense'
    model = Expense
    template_name = 'finance/expense_detail.html'
    context_object_name = 'expense'


class ExpenseApproveView(WMSPermissionMixin, View):
    permission_required = 'finance.approve_expense'

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        if expense.status != 'pending_approval':
            messages.error(request, "This expense is not pending approval.")
            return redirect('finance:expense-detail', pk=pk)

        approval_request = ApprovalRequest.objects.filter(
            action='expense',
            object_id=expense.pk,
            status='pending'
        ).first()

        if not approval_request:
            messages.error(request, "No pending approval request found.")
            return redirect('finance:expense-detail', pk=pk)

        action = request.POST.get('action')
        try:
            if action == 'approve':
                approve_request(approval_request, request.user)
                expense.status = 'approved'
                expense.approved_by = request.user
                expense.save()
                create_expense_journal_entry(expense)
                log_activity(
                    request.user,
                    f"Approved expense {expense.reference}",
                    "Finance",
                    request=request
                )
                messages.success(request, "Expense approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_request(approval_request, request.user, reason)
                expense.status = 'rejected'
                expense.save()
                log_activity(
                    request.user,
                    f"Rejected expense {expense.reference}",
                    "Finance",
                    request=request
                )
                messages.warning(request, "Expense rejected.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('finance:expense-detail', pk=pk)


class ExpensePayView(WMSPermissionMixin, View):
    permission_required = 'finance.pay_expense'

    def post(self, request, pk):
        expense = get_object_or_404(Expense, pk=pk)
        if expense.status != 'approved':
            messages.error(request, "Only approved expenses can be paid.")
            return redirect('finance:expense-detail', pk=pk)

        expense.status = 'paid'
        expense.paid_by = request.user
        # ✅ FIX: default to uppercase 'CASH'
        expense.payment_method = request.POST.get('payment_method', 'CASH')
        expense.save()

        log_activity(
            request.user,
            f"Paid expense {expense.reference}",
            "Finance",
            request=request
        )
        messages.success(request, "Expense marked as paid.")
        return redirect('finance:expense-detail', pk=pk)