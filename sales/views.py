# sales/views.py
from datetime import timedelta
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum
from django.http import HttpResponse
from django.core.exceptions import ValidationError

from core.mixins import WMSPermissionMixin
from .models import (
    Customer, Quotation, QuotationItem, SalesOrder, SalesOrderItem,
    Invoice, InvoiceItem, Payment
)
from .forms import (
    CustomerForm, QuotationForm, QuotationItemFormSet,
    SalesOrderForm, SalesOrderItemFormSet,
    InvoiceForm, PaymentForm
)

# ─── Document Services ──────────────────────────────
from documents.services.quotation import QuotationPDFService
from documents.services.sales_order import SalesOrderPDFService
from documents.services.invoice import InvoicePDFService
from documents.services.receipt import ReceiptPDFService


# ─── Customer Views ──────────────────────────────────

class CustomerListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_customer'
    model = Customer
    template_name = 'sales/customer_list.html'
    context_object_name = 'customers'


class CustomerCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'sales.add_customer'
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('sales:customer-list')


class CustomerUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'sales.change_customer'
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    success_url = reverse_lazy('sales:customer-list')


# ─── Quotation Views ──────────────────────────────────

class QuotationListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_quotation'
    model = Quotation
    template_name = 'sales/quotation_list.html'
    context_object_name = 'quotations'

    def get_queryset(self):
        qs = super().get_queryset().select_related('customer', 'created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Quotation.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class QuotationCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'sales.add_quotation'
    model = Quotation
    form_class = QuotationForm
    template_name = 'sales/quotation_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = QuotationItemFormSet(self.request.POST)
        else:
            ctx['formset'] = QuotationItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            quotation = form.save(commit=False)
            quotation.created_by = self.request.user
            quotation.save()
            formset.instance = quotation
            formset.save()

            # Generate PDF
            try:
                service = QuotationPDFService(quotation)
                service.save_to_object()
            except Exception:
                pass

            messages.success(self.request, f"Quotation {quotation.reference} created.")
            return redirect('sales:quotation-detail', pk=quotation.pk)
        return self.render_to_response(ctx)


class QuotationDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_quotation'
    model = Quotation
    template_name = 'sales/quotation_detail.html'
    context_object_name = 'quotation'


class QuotationUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'sales.change_quotation'
    model = Quotation
    form_class = QuotationForm
    template_name = 'sales/quotation_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = QuotationItemFormSet(self.request.POST, instance=self.object)
        else:
            ctx['formset'] = QuotationItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

            # Regenerate PDF
            try:
                service = QuotationPDFService(self.object)
                service.save_to_object()
            except Exception:
                pass

            messages.success(self.request, "Quotation updated.")
            return redirect('sales:quotation-detail', pk=self.object.pk)
        return self.render_to_response(ctx)


class QuotationAcceptView(WMSPermissionMixin, View):
    """Accept a quotation – automatically creates Sales Order and Invoice."""
    permission_required = 'sales.change_quotation'

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.status = 'accepted'
        quotation.save()

        # ─── Create Sales Order ──────────────────────────
        order = SalesOrder.objects.create(
            customer=quotation.customer,
            quotation=quotation,
            status='approved',
            discount_amount=quotation.discount_amount,
            notes=f"Converted from {quotation.reference}",
            created_by=request.user,
        )

        for item in quotation.items.all():
            SalesOrderItem.objects.create(
                order=order,
                item=item.item,
                quantity=item.quantity,
                unit_price=item.unit_price,
                notes=item.notes,
            )

        # Generate Order PDF
        try:
            service = SalesOrderPDFService(order)
            service.save_to_object()
        except Exception:
            pass

        # ─── Create Invoice ──────────────────────────────
        invoice = Invoice.objects.create(
            customer=quotation.customer,
            sales_order=order,
            due_date=order.order_date + timedelta(days=30),
            total_amount=order.total_amount,
            notes=f"Auto-generated from {order.reference}",
            created_by=request.user,
        )

        for item in order.items.all():
            InvoiceItem.objects.create(
                invoice=invoice,
                item=item.item,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total=item.total,
            )

        # ─── Update order status to 'invoiced' ──────────
        order.status = 'invoiced'
        order.save(update_fields=['status'])

        # Generate Invoice PDF
        try:
            service = InvoicePDFService(invoice)
            service.save_to_object()
        except Exception:
            pass

        messages.success(
            request,
            f"Quotation accepted. Order {order.reference} and Invoice {invoice.reference} created."
        )
        return redirect('sales:invoice-detail', pk=invoice.pk)


class QuotationPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        if quotation.pdf_file and quotation.pdf_file.storage.exists(quotation.pdf_file.name):
            response = HttpResponse(quotation.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{quotation.pdf_file.name}"'
            return response
        service = QuotationPDFService(quotation)
        service.save_to_object()
        return service.render_to_response()


class QuotationSendView(WMSPermissionMixin, View):
    permission_required = 'sales.change_quotation'

    def post(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        if quotation.status == 'draft':
            quotation.status = 'sent'
            quotation.save()
            messages.success(request, f"Quotation {quotation.reference} marked as sent.")
        else:
            messages.error(request, "This quotation cannot be sent.")
        return redirect('sales:quotation-detail', pk=pk)


class QuotationEmailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quotation = get_object_or_404(Quotation, pk=pk)
        if not quotation.customer.email:
            messages.error(request, "Customer has no email address.")
            return redirect('sales:quotation-detail', pk=pk)
        service = QuotationPDFService(quotation)
        try:
            service.email(
                recipient=quotation.customer.email,
                subject=f"Quotation {quotation.reference}",
                message="Please find your quotation attached."
            )
            messages.success(request, f"Quotation sent to {quotation.customer.email}")
        except Exception as e:
            messages.error(request, f"Failed to send: {e}")
        return redirect('sales:quotation-detail', pk=pk)


# ─── Sales Order Views ─────────────────────────────────

class SalesOrderListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_salesorder'
    model = SalesOrder
    template_name = 'sales/order_list.html'
    context_object_name = 'orders'

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


class SalesOrderDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_salesorder'
    model = SalesOrder
    template_name = 'sales/order_detail.html'
    context_object_name = 'order'


class SalesOrderPDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(SalesOrder, pk=pk)
        if order.pdf_file and order.pdf_file.storage.exists(order.pdf_file.name):
            response = HttpResponse(order.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{order.pdf_file.name}"'
            return response
        service = SalesOrderPDFService(order)
        service.save_to_object()
        return service.render_to_response()
    
# sales/views.py – add this class (anywhere after imports)

class SalesOrderEmailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(SalesOrder, pk=pk)
        if not order.customer.email:
            messages.error(request, "Customer has no email address.")
            return redirect('sales:order-detail', pk=pk)
        service = SalesOrderPDFService(order)
        try:
            service.email(
                recipient=order.customer.email,
                subject=f"Sales Order {order.reference}",
                message="Please find attached your sales order."
            )
            messages.success(request, f"Sales Order sent to {order.customer.email}")
        except Exception as e:
            messages.error(request, f"Failed to send: {e}")
        return redirect('sales:order-detail', pk=pk)


# ─── Invoice Views ──────────────────────────────────────

class InvoiceListView(WMSPermissionMixin, ListView):
    permission_required = 'sales.view_invoice'
    model = Invoice
    template_name = 'sales/invoice_list.html'
    context_object_name = 'invoices'

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


class InvoiceDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_invoice'
    model = Invoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'


class InvoicePDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if invoice.pdf_file and invoice.pdf_file.storage.exists(invoice.pdf_file.name):
            response = HttpResponse(invoice.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{invoice.pdf_file.name}"'
            return response
        service = InvoicePDFService(invoice)
        service.save_to_object()
        return service.render_to_response()


class InvoiceEmailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        if not invoice.customer.email:
            messages.error(request, "Customer has no email address.")
            return redirect('sales:invoice-detail', pk=pk)
        service = InvoicePDFService(invoice)
        try:
            service.email(
                recipient=invoice.customer.email,
                subject=f"Invoice {invoice.reference}",
                message="Please find attached your invoice."
            )
            messages.success(request, f"Invoice sent to {invoice.customer.email}")
        except Exception as e:
            messages.error(request, f"Failed to send: {e}")
        return redirect('sales:invoice-detail', pk=pk)


# ─── Payment Views ──────────────────────────────────────

class PaymentCreateView(WMSPermissionMixin, View):
    permission_required = 'sales.receive_payment'

    def get(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        form = PaymentForm()
        return render(request, 'sales/payment_form.html', {'form': form, 'invoice': invoice})

    def post(self, request, invoice_pk):
        invoice = get_object_or_404(Invoice, pk=invoice_pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.received_by = request.user
            payment.save()

            # Update invoice
            invoice.paid_amount = invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
            invoice.status = 'paid' if invoice.balance_due == 0 else 'partially_paid'
            invoice.save()

            # Generate receipt
            try:
                service = ReceiptPDFService(payment)
                service.save_to_object()
            except Exception:
                pass

            messages.success(request, f"Payment recorded. Receipt {payment.receipt_number} generated.")
            return redirect('sales:invoice-detail', pk=invoice.pk)

        return render(request, 'sales/payment_form.html', {'form': form, 'invoice': invoice})