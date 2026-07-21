# sales/views.py
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Sum
from django.core.exceptions import ValidationError
from company_settings.models import ApprovalRequest
from company_settings.services import (
    approve_request, create_approval_request, get_approval_required,
    notify_approvers, reject_request, user_can_approve
)
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity
from inventory.models import Warehouse
from inventory.services import issue_stock
from finance.services import create_sales_payment_journal_entry
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from decimal import Decimal
from company_settings.services import get_company, get_setting
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
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            discount = form.cleaned_data.get('discount_amount', 0)

            # ─── Approval logic ─────────────────────────────────────
            if discount > 0:
                required_role = get_approval_required('sales_discount', discount)
                if required_role and not user_can_approve(self.request.user, 'sales_discount', discount):
                    # Needs approval → pending
                    self.object.status = 'pending_approval'
                    self.object.save()
                    formset.instance = self.object
                    formset.save()
                    create_approval_request(
                        user=self.request.user,
                        action='sales_discount',
                        amount=discount,
                        reference=self.object.reference,
                        notes=f"Discount on {self.object.reference}",
                        content_object=self.object
                    )
                    messages.warning(self.request, "Discount requires approval. Notified manager.")
                    return redirect('sales:order-detail', pk=self.object.pk)
                else:
                    # Discount but user can approve → approved
                    self.object.status = 'approved'
            else:
                # No discount → auto‑approved
                self.object.status = 'approved'

            # ─── Save the order and items ──────────────────────────
            self.object.save()
            formset.instance = self.object
            formset.save()

            log_activity(self.request.user, f"Created sales order {self.object.reference}", "Sales", request=self.request)
            messages.success(self.request, f"Sales Order {self.object.reference} created.")

            # If the order is approved, offer to create invoice immediately
            if self.object.status == 'approved':
                messages.info(
                    self.request,
                    f"The order is approved. You can now create an invoice from the order detail page."
                )

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
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            self.object = form.save(commit=False)
            discount = form.cleaned_data.get('discount_amount', 0)

            # ─── Approval logic for updates ────────────────────────
            if discount > 0:
                required_role = get_approval_required('sales_discount', discount)
                if required_role and not user_can_approve(self.request.user, 'sales_discount', discount):
                    # Needs approval → pending
                    self.object.status = 'pending_approval'
                    self.object.save()
                    formset.instance = self.object
                    formset.save()
                    create_approval_request(
                        user=self.request.user,
                        action='sales_discount',
                        amount=discount,
                        reference=self.object.reference,
                        notes=f"Discount update on {self.object.reference}",
                        content_object=self.object
                    )
                    messages.warning(self.request, "Discount requires approval. Notified manager.")
                    return redirect('sales:order-detail', pk=self.object.pk)
                else:
                    # Discount but user can approve → approved
                    self.object.status = 'approved'
            else:
                # No discount → approved (if not already)
                self.object.status = 'approved'

            # ─── Save the order and items ──────────────────────────
            self.object.save()
            formset.instance = self.object
            formset.save()

            log_activity(self.request.user, f"Updated sales order {self.object.reference}", "Sales", request=self.request)
            messages.success(self.request, "Sales Order updated.")
            return redirect('sales:order-detail', pk=self.object.pk)
        return self.render_to_response(ctx)


# ─── Approval View ──────────────────────────────────────

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
                log_activity(
                    request.user,
                    f"Approved discount on {order.reference}",
                    "Sales",
                    request=request
                )
                messages.success(request, "Discount approved.")
            elif action == 'reject':
                reason = request.POST.get('reason', '')
                reject_request(approval_request, request.user, reason)
                order.status = 'draft'   # or 'cancelled' – we keep draft for editing
                order.save()
                log_activity(
                    request.user,
                    f"Rejected discount on {order.reference}",
                    "Sales",
                    request=request
                )
                messages.warning(request, "Discount rejected.")
            else:
                messages.error(request, "Invalid action.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('sales:order-detail', pk=pk)


# ─── Ready to Invoice Dashboard ─────────────────────────

class ReadyToInvoiceListView(WMSPermissionMixin, ListView):
    """
    Shows all approved sales orders that don't have an invoice yet.
    Provides a quick, one‑click way to create invoices.
    """
    permission_required = 'sales.view_salesorder'
    model = SalesOrder
    template_name = 'sales/ready_to_invoice.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        return SalesOrder.objects.filter(
            status='approved',
            invoices__isnull=True
        ).select_related('customer', 'created_by').order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Ready to Invoice'
        ctx['page_subtitle'] = 'Approved orders awaiting invoice creation'
        return ctx


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

        if hasattr(self, 'order'):
            invoice.sales_order = self.order

            # ─── Calculate total ──────────────────────────
            total = 0
            for item in self.order.items.all():
                total += item.total
            invoice.total_amount = total - self.order.discount_amount

            # ─── SAVE INVOICE FIRST ──────────────────────
            invoice.save()

            # ─── Now create items with the saved invoice ──
            for item in self.order.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=item.item,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total=item.total,
                )
        else:
            # Manual invoice – you would need a formset for items; for now we set total to 0.
            invoice.total_amount = 0
            invoice.save()

        log_activity(self.request.user, f"Created invoice {invoice.reference}", "Sales", request=self.request)
        messages.success(self.request, f"Invoice {invoice.reference} created.")
        return redirect('sales:invoice-detail', pk=invoice.pk)


class InvoiceDetailView(WMSPermissionMixin, DetailView):
    permission_required = 'sales.view_invoice'
    model = Invoice
    template_name = 'sales/invoice_detail.html'
    context_object_name = 'invoice'
    

class InvoicePrintView(LoginRequiredMixin, View):
    """
    Generate a PDF invoice for the given invoice ID.
    Uses the company profile for branding (logo, name, address, etc.)
    """
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        company = get_company()

        # Create the HttpResponse object with PDF headers.
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.reference}.pdf"'

        # Build the document
        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=1.5*cm
        )

        styles = getSampleStyleSheet()
        elements = []

        # ── Styles ─────────────────────────────────────────
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=4,
        )
        normal_style = styles['Normal']
        right_style = ParagraphStyle(
            'RightAlign',
            parent=normal_style,
            alignment=TA_RIGHT,
        )
        center_style = ParagraphStyle(
            'CenterAlign',
            parent=normal_style,
            alignment=TA_CENTER,
        )
        bold_style = ParagraphStyle(
            'Bold',
            parent=normal_style,
            fontName='Helvetica-Bold',
        )

        # ── Header: Company info ──────────────────────────
        if company and company.logo:
            # We could add logo image here, but reportlab requires file path.
            # For simplicity, we skip logo; you can add it later.
            pass

        elements.append(Paragraph(company.name if company else "J&N WMS", title_style))
        elements.append(Paragraph(company.trading_name if company else "Warehouse Management System", normal_style))
        if company:
            address = company.physical_address or company.postal_address or ''
            if company.city:
                address += f", {company.city}"
            if company.country:
                address += f", {company.country}"
            elements.append(Paragraph(address, normal_style))
            elements.append(Paragraph(f"Tel: {company.phone} | Email: {company.email}", normal_style))
        elements.append(Spacer(1, 0.3*cm))

        # ── Invoice Title ──────────────────────────────────
        elements.append(Paragraph("INVOICE", heading_style))
        elements.append(Paragraph(f"Reference: {invoice.reference}", normal_style))
        elements.append(Paragraph(f"Date: {invoice.invoice_date.strftime('%d %B %Y')}", normal_style))
        elements.append(Paragraph(f"Due Date: {invoice.due_date.strftime('%d %B %Y')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))

        # ── Customer Info ──────────────────────────────────
        elements.append(Paragraph("Bill To:", bold_style))
        elements.append(Paragraph(invoice.customer.name, normal_style))
        if invoice.customer.address:
            elements.append(Paragraph(invoice.customer.address, normal_style))
        if invoice.customer.phone:
            elements.append(Paragraph(f"Phone: {invoice.customer.phone}", normal_style))
        if invoice.customer.email:
            elements.append(Paragraph(f"Email: {invoice.customer.email}", normal_style))
        if invoice.customer.tax_id:
            elements.append(Paragraph(f"Tax ID: {invoice.customer.tax_id}", normal_style))
        elements.append(Spacer(1, 0.5*cm))

        # ── Items Table ────────────────────────────────────
        data = [['#', 'Item', 'Quantity', 'Unit Price', 'Total']]
        for idx, item in enumerate(invoice.items.all(), 1):
            data.append([
                str(idx),
                item.item.name,
                f"{item.quantity} {item.item.unit.symbol}",
                f"{item.unit_price:.2f}",
                f"{item.total:.2f}",
            ])

        # Add totals row
        data.append(['', '', '', 'Subtotal', f"{invoice.total_amount:.2f}"])
        # If discount amount > 0, add a row
        if invoice.sales_order and invoice.sales_order.discount_amount > 0:
            data.append(['', '', '', 'Discount', f"-{invoice.sales_order.discount_amount:.2f}"])
        data.append(['', '', '', 'Total', f"{invoice.total_amount:.2f}"])

        # Table styling
        col_widths = [1*cm, 6*cm, 3*cm, 3*cm, 3*cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#E2E8F0')),
            ('BACKGROUND', (0,1), (-1,-2), colors.white),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#F8FAFC')]),
            ('ALIGN', (1,1), (-1,-1), 'LEFT'),
            ('ALIGN', (2,1), (-1,-1), 'CENTER'),
            # Total row style
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9')),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (3,-1), (-1,-1), 'RIGHT'),
        ]))
        elements.append(table)

        # ── Payment Terms ──────────────────────────────────
        elements.append(Spacer(1, 0.5*cm))
        payment_terms = get_setting('DEFAULT_PAYMENT_TERMS', 'Net 30')
        elements.append(Paragraph(f"Payment Terms: {payment_terms}", normal_style))

        # ── Footer ─────────────────────────────────────────
        elements.append(Spacer(1, 0.5*cm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0')))
        elements.append(Paragraph("Thank you for your business!", center_style))
        if company:
            elements.append(Paragraph(company.name, center_style))

        # Build the PDF
        doc.build(elements)
        return response


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

        self.invoice.paid_amount = self.invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
        self.invoice.status = 'paid' if self.invoice.balance_due == 0 else 'partially_paid'
        self.invoice.save()

        # ─── Create Journal Entry ──────────────────────────
        create_sales_payment_journal_entry(payment)

        # ─── Reduce Stock (with error handling) ─────────────
        if self.invoice.sales_order:
            for item in self.invoice.items.all():
                if item.quantity > 0:
                    warehouse = self.invoice.sales_order.warehouse or Warehouse.objects.filter(is_active=True).first()
                    if warehouse:
                        try:
                            issue_stock(
                                item=item.item,
                                warehouse=warehouse,
                                quantity=item.quantity,
                                reference=self.invoice.reference,
                                notes=f"Issued from sales invoice {self.invoice.reference}",
                                user=self.request.user,
                            )
                        except ValidationError as e:
                            error_msg = str(e)
                            messages.warning(
                                self.request,
                                f"Stock issue failed for {item.item.name}: {error_msg}"
                            )
                            log_activity(
                                self.request.user,
                                f"Stock issue failed for invoice {self.invoice.reference}: {error_msg}",
                                "Sales",
                                request=self.request
                            )

        log_activity(self.request.user, f"Received payment {payment.amount} for invoice {self.invoice.reference}", "Sales", request=self.request)
        messages.success(self.request, f"Payment received. Receipt printed.")
        return redirect('sales:invoice-detail', pk=self.invoice.pk)