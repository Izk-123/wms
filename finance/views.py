from decimal import Decimal, InvalidOperation

from django.views.generic import ListView, CreateView, DetailView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from company_settings.models import ApprovalRequest
from company_settings.services import (
    approve_request, create_approval_request, get_approval_required,
    reject_request, user_can_approve
)
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity
from hr.models import Department
from sales.models import Payment
from .models import (
    Account, BankAccount, BankStatement, BankTransaction, Budget, FinanceAuditLog, FiscalPeriod, JournalEntry, Expense, CashDrawer, CashTransaction, SupplierBill,
)
from .forms import (
    AccountForm, BankReconciliationForm, BankStatementUploadForm, BudgetForm, ExpenseForm, FiscalPeriodForm, SupplierBillForm, OpenDrawerForm, CloseDrawerForm,
)
from .services import (
    close_fiscal_period, create_expense_journal_entry, create_supplier_bill_journal_entry,
    create_supplier_payment_journal_entry, finalize_reconciliation, get_actual_expenses, import_bank_statements, match_bank_transaction, open_cash_drawer, close_cash_drawer,
    record_cash_payment, log_finance_audit, snapshot,
)


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
            log_finance_audit(
                self.request.user, "Created expense (pending approval)", expense,
                request=self.request
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
        log_finance_audit(
            self.request.user, "Created expense (auto-approved)", expense,
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
        before = snapshot(expense)
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
                log_finance_audit(
                    request.user, "Approved expense", expense,
                    before=before, request=request
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
                log_finance_audit(
                    request.user, "Rejected expense", expense,
                    before=before, reason=reason, request=request
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

        before = snapshot(expense)
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
        log_finance_audit(
            request.user, "Paid expense", expense,
            before=before, request=request
        )

        # If a cash drawer is open for this user and paid via cash, record the outflow
        if expense.payment_method == 'CASH':
            drawer = CashDrawer.objects.filter(cashier=request.user, status='open').first()
            if drawer:
                record_cash_payment(
                    drawer=drawer,
                    amount=expense.amount,
                    description=f"Expense {expense.reference}",
                    reference=expense.reference,
                    transaction_type='expense',
                    user=request.user,
                )

        messages.success(request, "Expense marked as paid.")
        return redirect('finance:expense-detail', pk=pk)


# ─── Cashier Workspace ──────────────────────────────────

class CashierDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'finance/cashier_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        drawer = CashDrawer.objects.filter(cashier=self.request.user, status='open').first()
        ctx['drawer'] = drawer
        ctx['open_form'] = OpenDrawerForm()
        ctx['close_form'] = CloseDrawerForm()

        ctx['today_collections'] = Payment.objects.filter(
            received_by=self.request.user,
            payment_date__date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        if drawer:
            ctx['today_transactions'] = drawer.transactions.order_by('-created_at')[:15]
            cash_in = drawer.transactions.filter(
                transaction_type__in=['payment_in', 'refund']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            cash_out = drawer.transactions.filter(
                transaction_type__in=['payment_out', 'expense']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            ctx['drawer_cash_in'] = cash_in
            ctx['drawer_cash_out'] = cash_out
            ctx['drawer_running_balance'] = drawer.opening_balance + cash_in - cash_out
        else:
            ctx['today_transactions'] = []
            ctx['drawer_cash_in'] = Decimal('0.00')
            ctx['drawer_cash_out'] = Decimal('0.00')
            ctx['drawer_running_balance'] = Decimal('0.00')

        ctx['recent_drawers'] = CashDrawer.objects.filter(
            cashier=self.request.user, status='closed'
        ).order_by('-closed_at')[:5]
        return ctx


class OpenDrawerView(WMSPermissionMixin, View):
    permission_required = 'finance.manage_cash_drawer'

    def post(self, request):
        form = OpenDrawerForm(request.POST)
        if form.is_valid():
            try:
                drawer = open_cash_drawer(
                    request.user,
                    opening_balance=form.cleaned_data['opening_balance']
                )
                log_activity(
                    request.user,
                    f"Opened cash drawer with balance {drawer.opening_balance}",
                    "Finance",
                    request=request
                )
                log_finance_audit(request.user, "Opened cash drawer", drawer, request=request)
                messages.success(request, f"Cash drawer opened with balance {drawer.opening_balance}.")
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please enter a valid opening balance.")
        return redirect('finance:cashier-dashboard')


class CloseDrawerView(WMSPermissionMixin, View):
    permission_required = 'finance.manage_cash_drawer'

    def post(self, request):
        drawer = get_object_or_404(CashDrawer, cashier=request.user, status='open')
        form = CloseDrawerForm(request.POST)
        if form.is_valid():
            before = snapshot(drawer)
            try:
                close_cash_drawer(drawer, form.cleaned_data['closing_balance'])
                log_activity(
                    request.user,
                    f"Closed cash drawer (difference: {drawer.difference})",
                    "Finance",
                    request=request
                )
                log_finance_audit(
                    request.user, "Closed cash drawer", drawer,
                    before=before, request=request
                )
                messages.success(request, f"Cash drawer closed. Difference: {drawer.difference}")
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please enter a valid closing balance.")
        return redirect('finance:cashier-dashboard')


# ─── Accounts Payable / Supplier Bill Views ─────────────

class SupplierBillListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_supplierbill'
    model = SupplierBill
    template_name = 'finance/supplier_bill_list.html'
    context_object_name = 'bills'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('supplier', 'created_by', 'approved_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = SupplierBill.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class SupplierBillCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'finance.add_supplierbill'
    model = SupplierBill
    form_class = SupplierBillForm
    template_name = 'finance/supplier_bill_form.html'

    def form_valid(self, form):
        bill = form.save(commit=False)
        bill.created_by = self.request.user
        amount = bill.amount
        required_role = get_approval_required('supplier_bill', amount)
        if required_role and not user_can_approve(self.request.user, 'supplier_bill', amount):
            bill.status = 'pending_approval'
            bill.save()
            create_approval_request(
                user=self.request.user,
                action='supplier_bill',
                amount=amount,
                reference=bill.reference,
                notes=bill.description,
                content_object=bill
            )
            log_finance_audit(
                self.request.user, "Created supplier bill (pending approval)", bill,
                request=self.request
            )
            messages.info(self.request, "Supplier bill submitted for approval.")
            return redirect('finance:supplier-bill-list')

        bill.status = 'approved'
        bill.approved_by = self.request.user
        bill.save()
        create_supplier_bill_journal_entry(bill)
        log_activity(
            self.request.user,
            f"Created supplier bill {bill.reference}",
            "Finance",
            request=self.request
        )
        log_finance_audit(
            self.request.user, "Created supplier bill (auto-approved)", bill,
            request=self.request
        )
        messages.success(self.request, "Supplier bill recorded.")
        return redirect('finance:supplier-bill-detail', pk=bill.pk)


class SupplierBillDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'finance.view_supplierbill'
    model = SupplierBill
    template_name = 'finance/supplier_bill_detail.html'
    context_object_name = 'bill'


class SupplierBillApproveView(WMSPermissionMixin, View):
    permission_required = 'finance.approve_supplierbill'

    def post(self, request, pk):
        bill = get_object_or_404(SupplierBill, pk=pk)
        if bill.status != 'pending_approval':
            messages.error(request, "This bill is not pending approval.")
            return redirect('finance:supplier-bill-detail', pk=pk)

        approval_request = ApprovalRequest.objects.filter(
            action='supplier_bill',
            object_id=bill.pk,
            status='pending'
        ).first()

        if not approval_request:
            messages.error(request, "No pending approval request found.")
            return redirect('finance:supplier-bill-detail', pk=pk)

        action = request.POST.get('action')
        before = snapshot(bill)
        try:
            if action == 'approve':
                approve_request(approval_request, request.user)
                bill.status = 'approved'
                bill.approved_by = request.user
                bill.save()
                create_supplier_bill_journal_entry(bill)
                log_activity(
                    request.user,
                    f"Approved supplier bill {bill.reference}",
                    "Finance",
                    request=request
                )
                log_finance_audit(
                    request.user, "Approved supplier bill", bill,
                    before=before, request=request
                )
                messages.success(request, "Supplier bill approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_request(approval_request, request.user, reason)
                bill.status = 'rejected'
                bill.save()
                log_activity(
                    request.user,
                    f"Rejected supplier bill {bill.reference}",
                    "Finance",
                    request=request
                )
                log_finance_audit(
                    request.user, "Rejected supplier bill", bill,
                    before=before, reason=reason, request=request
                )
                messages.warning(request, "Supplier bill rejected.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('finance:supplier-bill-detail', pk=pk)


class SupplierBillPayView(WMSPermissionMixin, View):
    permission_required = 'finance.pay_supplierbill'

    def post(self, request, pk):
        bill = get_object_or_404(SupplierBill, pk=pk)
        if bill.status != 'approved':
            messages.error(request, "Only approved bills can be paid.")
            return redirect('finance:supplier-bill-detail', pk=pk)

        raw_amount = request.POST.get('amount', str(bill.balance_due))
        try:
            payment_amount = Decimal(raw_amount)
        except (InvalidOperation, TypeError):
            messages.error(request, "Invalid payment amount.")
            return redirect('finance:supplier-bill-detail', pk=pk)

        if payment_amount <= 0 or payment_amount > bill.balance_due:
            messages.error(request, "Payment amount must be between 0 and the outstanding balance.")
            return redirect('finance:supplier-bill-detail', pk=pk)

        before = snapshot(bill)
        bill.paid_amount += payment_amount
        bill.paid_by = request.user
        bill.payment_method = request.POST.get('payment_method', 'CASH')
        if bill.paid_amount >= bill.amount:
            bill.status = 'paid'
        bill.save()

        create_supplier_payment_journal_entry(bill, payment_amount)

        log_activity(
            request.user,
            f"Paid {payment_amount} on supplier bill {bill.reference}",
            "Finance",
            request=request
        )
        log_finance_audit(
            request.user, "Paid supplier bill", bill,
            before=before, request=request
        )

        if bill.payment_method == 'CASH':
            drawer = CashDrawer.objects.filter(cashier=request.user, status='open').first()
            if drawer:
                record_cash_payment(
                    drawer=drawer,
                    amount=payment_amount,
                    description=f"Supplier bill {bill.reference}",
                    reference=bill.reference,
                    transaction_type='payment_out',
                    user=request.user,
                )

        messages.success(request, "Payment recorded.")
        return redirect('finance:supplier-bill-detail', pk=pk)

# ─── Bank Reconciliation Views ────────────────────────────────────

class BankAccountListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_bankaccount'
    model = BankAccount
    template_name = 'finance/bank_account_list.html'
    context_object_name = 'accounts'


class BankReconciliationView(WMSPermissionMixin, View):
    permission_required = 'finance.reconcile_bank'
    template_name = 'finance/bank_reconciliation.html'

    def get(self, request, account_id):
        account = get_object_or_404(BankAccount, pk=account_id)
        transactions = account.transactions.filter(reconciled=False).order_by('date')
        statements = account.statements.filter(reconciled=False).order_by('statement_date')
        context = {
            'account': account,
            'transactions': transactions,
            'statements': statements,
            'reconciliation_form': BankReconciliationForm(),
        }
        return render(request, self.template_name, context)

    def post(self, request, account_id):
        account = get_object_or_404(BankAccount, pk=account_id)
        action = request.POST.get('action')

        if action == 'match':
            tx_id = request.POST.get('transaction_id')
            stmt_id = request.POST.get('statement_id')
            tx = get_object_or_404(BankTransaction, pk=tx_id, account=account)
            stmt = get_object_or_404(BankStatement, pk=stmt_id, account=account)
            try:
                match_bank_transaction(tx, stmt, request.user)
                messages.success(request, "Transaction matched.")
            except ValidationError as e:
                messages.error(request, str(e))

        elif action == 'complete':
            form = BankReconciliationForm(request.POST)
            if form.is_valid():
                try:
                    finalize_reconciliation(
                        account,
                        timezone.now().date(),
                        form.cleaned_data['opening_balance'],
                        form.cleaned_data['closing_balance'],
                        request.user
                    )
                    messages.success(request, "Reconciliation completed.")
                except ValidationError as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, "Please correct the form errors.")

        return redirect('finance:bank-reconciliation', account_id=account_id)


class ImportBankStatementView(WMSPermissionMixin, View):
    permission_required = 'finance.reconcile_bank'

    def post(self, request):
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            account = form.cleaned_data['account']
            file = request.FILES['statement_file']
            try:
                count = import_bank_statements(account, file)
                messages.success(request, f"Imported {count} statement lines.")
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
        else:
            messages.error(request, "Invalid form.")
        return redirect('finance:bank-account-list')


# ─── Budget Views ──────────────────────────────────────────────────

class BudgetListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_budget'
    model = Budget
    template_name = 'finance/budget_list.html'
    context_object_name = 'budgets'


class BudgetCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'finance.add_budget'
    model = Budget
    form_class = BudgetForm
    template_name = 'finance/budget_form.html'
    success_url = reverse_lazy('finance:budget-list')


class BudgetUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'finance.change_budget'
    model = Budget
    form_class = BudgetForm
    template_name = 'finance/budget_form.html'
    success_url = reverse_lazy('finance:budget-list')


class BudgetVsActualView(WMSPermissionMixin, TemplateView):
    permission_required = 'finance.view_budget'
    template_name = 'finance/budget_vs_actual.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', timezone.now().year))
        department_id = self.request.GET.get('department')

        budgets = Budget.objects.filter(fiscal_year=year)
        if department_id:
            budgets = budgets.filter(department_id=department_id)

        report = []
        for budget in budgets:
            actual = get_actual_expenses(budget.department, year)
            # If you have budget lines, you could break down by category.
            variance = budget.amount - actual
            report.append({
                'department': budget.department.name if budget.department else 'General',
                'budget': budget.amount,
                'actual': actual,
                'variance': variance,
                'percentage': (actual / budget.amount * 100) if budget.amount else 0,
            })

        ctx['report'] = report
        ctx['year'] = year
        ctx['departments'] = Department.objects.filter(is_active=True)
        ctx['selected_department'] = department_id
        return ctx


# ─── Fiscal Period Views ───────────────────────────────────────────

class FiscalPeriodListView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_fiscalperiod'
    model = FiscalPeriod
    template_name = 'finance/period_list.html'
    context_object_name = 'periods'


class FiscalPeriodCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'finance.add_fiscalperiod'
    model = FiscalPeriod
    form_class = FiscalPeriodForm
    template_name = 'finance/period_form.html'
    success_url = reverse_lazy('finance:period-list')


class ClosePeriodView(WMSPermissionMixin, View):
    permission_required = 'finance.close_period'

    def post(self, request, pk):
        period = get_object_or_404(FiscalPeriod, pk=pk)
        try:
            close_fiscal_period(period, request.user)
            messages.success(request, f"Period {period.name} closed.")
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('finance:period-list')


# ─── Audit Log View (already exists in models but we expose it) ──

class AuditLogView(WMSPermissionMixin, ListView):
    permission_required = 'finance.view_auditlog'
    model = FinanceAuditLog
    template_name = 'finance/audit_log.html'
    context_object_name = 'logs'
    paginate_by = 50
    ordering = ['-created_at']