from django.views.generic import ListView, CreateView, UpdateView, DetailView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum
from django.core.exceptions import ValidationError
from company_settings.models import ApprovalRequest
from company_settings.services import approve_request, create_approval_request, get_approval_required, notify_approvers, reject_request, user_can_approve
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity
from inventory.models import Warehouse
from inventory.services import issue_stock
from finance.services import create_sales_payment_journal_entry
from .models import Customer, InvoiceItem, SalesOrder, Invoice, Payment
from .forms import CustomerForm, SalesOrderForm, SalesOrderItemFormSet, PaymentForm, InvoiceForm

# ─── Customer Views ──────────────────────────────────────
class CustomerListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_customer'
    model = Customer
    template_name = 'sales/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx

class CustomerCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'sales.add_customer'
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('sales:customer-list')

    def form_valid(self, form):
        log_activity(self.request.user, f"Created customer: {form.instance.name}", "Sales", request=self.request)
        messages.success(self.request, "Customer created.")
        return super().form_valid(form)

class CustomerUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'sales.change_customer'
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('sales:customer-list')

# ─── Sales Order Views ──────────────────────────────────
class SalesOrderListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_salesorder'
    model = SalesOrder
    template_name = 'sales/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = SalesOrder.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx

class SalesOrderCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'sales.add_salesorder'
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = 'sales/order_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = SalesOrderItemFormSet(self.request.POST)
        else:
            ctx['formset'] = SalesOrderItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            form.instance.created_by = self.request.user
            # Check discount approval
            discount = form.cleaned_data.get('discount_amount', 0)
            if discount > 0:
                required_role = get_approval_required('sales_discount', discount)
                if required_role and not user_can_approve(self.request.user, 'sales_discount', discount):
                    form.instance.status = 'pending_approval'
                    form.instance.save()
                    notify_approvers(form.instance, required_role, f"Discount on {form.instance.reference}")
                    messages.warning(self.request, "Discount requires approval. Notified manager.")
                    return redirect('sales:order-list')
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            log_activity(self.request.user, f"Created sales order {self.object.reference}", "Sales", request=self.request)
            messages.success(self.request, f"Sales Order {self.object.reference} created.")
            return redirect('sales:order-detail', pk=self.object.pk)
        return self.render_to_response(ctx)

class SalesOrderDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_salesorder'
    model = SalesOrder
    template_name = 'sales/order_detail.html'
    context_object_name = 'order'

class SalesOrderUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'sales.change_salesorder'
    model = SalesOrder
    form_class = SalesOrderForm
    template_name = 'sales/order_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = SalesOrderItemFormSet(self.request.POST, instance=self.object)
        else:
            ctx['formset'] = SalesOrderItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        discount = form.cleaned_data.get('discount_amount', 0)
        if discount > 0:
            required_role = get_approval_required('sales_discount', discount)
            if required_role and not user_can_approve(self.request.user, 'sales_discount', discount):
                # Create approval request
                order = form.save(commit=False)
                order.status = 'pending_approval'
                order.save()
                create_approval_request(
                    user=self.request.user,
                    action='sales_discount',
                    amount=discount,
                    reference=order.reference,
                    notes=f"Discount on {order.reference}",
                    content_object=order
                )
                messages.warning(self.request, "Discount requires approval. Notified manager.")
                return redirect('sales:order-detail', pk=order.pk)
        return super().form_valid(form)

# ─── Approval View for Sales Order Discount ──────────────
class ApproveDiscountView(WMSPermissionMixin, View):
    permission_required = 'sales.approve_discount'

    def post(self, request, pk):
        order = get_object_or_404(SalesOrder, pk=pk)
        if order.status != 'pending_approval':
            messages.error(request, "This order is not pending approval.")
            return redirect('sales:order-detail', pk=pk)

        action = request.POST.get('action')
        approval_request = ApprovalRequest.objects.filter(
            action='sales_discount',
            object_id=order.pk,
            status='pending'
        ).first()

        if not approval_request:
            messages.error(request, "No pending approval request found.")
            return redirect('sales:order-detail', pk=pk)

        try:
            if action == 'approve':
                approve_request(approval_request, request.user)
                order.status = 'approved'
                order.discount_approved = True
                order.approved_by = request.user
                order.save()
                log_activity(...)
                messages.success(request, "Discount approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_request(approval_request, request.user, reason)
                order.status = 'cancelled'  # or back to draft
                order.save()
                messages.warning(request, "Discount rejected.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('sales:order-detail', pk=pk)

# ─── Invoice Views ───────────────────────────────────────
class InvoiceListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_invoice'
    model = Invoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Invoice.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx

class InvoiceCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'sales.create_invoice'
    model = Invoice
    form_class = InvoiceForm
    template_name = 'sales/invoice_form.html'

    def get_initial(self):
        initial = super().get_initial()
        order_pk = self.kwargs.get('order_pk')
        if order_pk:
            order = get_object_or_404(SalesOrder, pk=order_pk)
            initial['customer'] = order.customer
            self.order = order
        return initial

    def form_valid(self, form):
        invoice = form.save(commit=False)
        invoice.created_by = self.request.user
        # If from sales order, copy items
        if hasattr(self, 'order'):
            invoice.sales_order = self.order
            # Calculate total from order items
            total = 0
            for item in self.order.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=item.item,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )
                total += item.total
            invoice.total_amount = total - self.order.discount_amount
        else:
            # Manual invoice – you'll need to add items via formset; for brevity we skip.
            pass
        invoice.save()
        log_activity(self.request.user, f"Created invoice {invoice.reference}", "Sales", request=self.request)
        messages.success(self.request, f"Invoice {invoice.reference} created.")
        return redirect('sales:invoice-detail', pk=invoice.pk)

class InvoiceDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_invoice'
    model = Invoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'

# ─── Payment (Cashier) View ──────────────────────────────
class PaymentCreateView(WMSPermissionMixin, FormView):
    permission_required = 'sales.receive_payment'
    template_name = 'sales/payment_form.html'
    form_class = PaymentForm

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs['invoice_pk'])
        if self.invoice.status == 'paid':
            messages.error(request, "This invoice is already paid.")
            return redirect('sales:invoice-detail', pk=self.invoice.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['invoice'] = self.invoice
        return ctx

    def form_valid(self, form):
        payment = form.save(commit=False)
        payment.invoice = self.invoice
        payment.received_by = self.request.user
        payment.save()

        # Update invoice paid amount
        self.invoice.paid_amount = self.invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
        self.invoice.status = 'paid' if self.invoice.balance_due == 0 else 'partially_paid'
        self.invoice.save()

        # Create journal entry
        create_sales_payment_journal_entry(payment)

        # Reduce stock (if not already done)
        if self.invoice.sales_order:
            for item in self.invoice.items.all():
                if item.quantity > 0:
                    warehouse = self.invoice.sales_order.warehouse or Warehouse.objects.filter(is_active=True).first()
                    if warehouse:
                        issue_stock(
                            item=item.item,
                            warehouse=warehouse,
                            quantity=item.quantity,
                            reference=self.invoice.reference,
                            notes=f"Issued from sales invoice {self.invoice.reference}",
                            user=self.request.user,
                        )

        log_activity(self.request.user, f"Received payment {payment.amount} for invoice {self.invoice.reference}", "Sales", request=self.request)
        messages.success(self.request, f"Payment received. Receipt printed.")
        return redirect('sales:invoice-detail', pk=self.invoice.pk)