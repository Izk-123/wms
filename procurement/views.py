# procurement/views.py
from datetime import timezone

from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.core.exceptions import ValidationError

from company_settings.models import ApprovalRequest
from company_settings.services import approve_request, create_approval_request, get_approval_required, reject_request, user_can_approve
from core.mixins import WMSPermissionMixin
from accounts.views import log_activity

from .models import (
    Supplier, PurchaseRequest, PurchaseOrder, GoodsReceipt
)
from .forms import (
    SupplierForm,
    PurchaseRequestForm, PurchaseRequestItemFormSet,
    PurchaseOrderForm, PurchaseOrderItemFormSet,
    GoodsReceiptForm, GoodsReceiptItemFormSet,
    RejectRequestForm,
)
from .services import (
    submit_purchase_request, approve_purchase_request,
    reject_purchase_request, confirm_goods_receipt,
)


# ─── Supplier Views ────────────────────────────────────────────

class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'procurement/supplier_list.html'
    context_object_name = 'suppliers'
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


class SupplierCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'procurement.add_supplier'
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier-list')

    def form_valid(self, form):
        log_activity(
            self.request.user,
            f"Created supplier: {form.instance.name}",
            "Procurement",
            request=self.request
        )
        messages.success(self.request, "Supplier added successfully.")
        return super().form_valid(form)


class SupplierUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'procurement.change_supplier'
    model = Supplier
    form_class = SupplierForm
    template_name = 'procurement/supplier_form.html'
    success_url = reverse_lazy('procurement:supplier-list')

    def form_valid(self, form):
        log_activity(
            self.request.user,
            f"Updated supplier: {form.instance.name}",
            "Procurement",
            request=self.request
        )
        messages.success(self.request, "Supplier updated successfully.")
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = 'procurement/supplier_detail.html'
    context_object_name = 'supplier'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['purchase_orders'] = self.object.purchase_orders.order_by(
            '-created_at'
        )[:10]
        return ctx


# ─── Purchase Request Views ────────────────────────────────────

class PurchaseRequestListView(LoginRequiredMixin, ListView):
    model = PurchaseRequest
    template_name = 'procurement/pr_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('requested_by', 'approved_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PurchaseRequest.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class PurchaseRequestCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'procurement.add_purchaserequest'
    model = PurchaseRequest
    form_class = PurchaseRequestForm
    template_name = 'procurement/pr_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = PurchaseRequestItemFormSet(self.request.POST)
        else:
            ctx['formset'] = PurchaseRequestItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            form.instance.requested_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            log_activity(
                self.request.user,
                f"Created Purchase Request: {self.object.reference}",
                "Procurement",
                request=self.request
            )
            messages.success(
                self.request,
                f"Purchase Request {self.object.reference} created."
            )
            return redirect('procurement:pr-detail', pk=self.object.pk)
        return self.render_to_response(ctx)


class PurchaseRequestDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseRequest
    template_name = 'procurement/pr_detail.html'
    context_object_name = 'pr'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reject_form'] = RejectRequestForm()
        return ctx

class PurchaseRequestActionView(WMSPermissionMixin, View):
    permission_required = 'procurement.approve_purchaserequest'

    def post(self, request, pk, action):
        pr = get_object_or_404(PurchaseRequest, pk=pk)

        if action == "submit":
            # Check if approval is needed
            amount = pr.items.aggregate(total=Sum('estimated_total'))['total'] or 0
            required_role = get_approval_required('purchase_request', amount)
            if required_role and not user_can_approve(request.user, 'purchase_request', amount):
                pr.status = 'pending_approval'
                pr.save()
                create_approval_request(
                    user=request.user,
                    action='purchase_request',
                    amount=amount,
                    reference=pr.reference,
                    notes=f"Purchase Request {pr.reference}",
                    content_object=pr
                )
                messages.info(request, "PR submitted for approval.")
            else:
                # No approval needed or user can self-approve
                pr.status = 'approved'
                pr.approved_by = request.user
                pr.approved_at = timezone.now()
                pr.save()
                messages.success(request, "PR approved.")
            return redirect('procurement:pr-detail', pk=pk)

        elif action == "approve":
            # Ensure user can approve
            amount = pr.items.aggregate(total=Sum('estimated_total'))['total'] or 0
            if not user_can_approve(request.user, 'purchase_request', amount):
                messages.error(request, "You do not have permission to approve this PR.")
                return redirect('procurement:pr-detail', pk=pk)

            approval_request = ApprovalRequest.objects.filter(
                action='purchase_request',
                object_id=pr.pk,
                status='pending'
            ).first()

            try:
                if approval_request:
                    approve_request(approval_request, request.user)
                pr.status = 'approved'
                pr.approved_by = request.user
                pr.approved_at = timezone.now()
                pr.save()
                messages.success(request, "PR approved.")
            except ValidationError as e:
                messages.error(request, str(e))

        elif action == "reject":
            form = RejectRequestForm(request.POST)
            if form.is_valid():
                reason = form.cleaned_data['reason']
                approval_request = ApprovalRequest.objects.filter(
                    action='purchase_request',
                    object_id=pr.pk,
                    status='pending'
                ).first()
                try:
                    if approval_request:
                        reject_request(approval_request, request.user, reason)
                    pr.status = 'rejected'
                    pr.approved_by = request.user
                    pr.approved_at = timezone.now()
                    pr.rejection_reason = reason
                    pr.save()
                    messages.success(request, "PR rejected.")
                except ValidationError as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, "Please provide a rejection reason.")

        return redirect('procurement:pr-detail', pk=pk)


# ─── Purchase Order Views ──────────────────────────────────────

class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'procurement/po_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('supplier', 'created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = PurchaseOrder.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class PurchaseOrderCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'procurement.add_purchaseorder'
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'procurement/po_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = PurchaseOrderItemFormSet(self.request.POST)
        else:
            ctx['formset'] = PurchaseOrderItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        formset = ctx['formset']
        if formset.is_valid():
            form.instance.created_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            # Link PR as ordered
            if self.object.purchase_request:
                self.object.purchase_request.status = "ordered"
                self.object.purchase_request.save()
            log_activity(
                self.request.user,
                f"Created PO {self.object.reference}",
                "Procurement",
                request=self.request
            )
            messages.success(
                self.request,
                f"Purchase Order {self.object.reference} created."
            )
            return redirect('procurement:po-detail', pk=self.object.pk)
        return self.render_to_response(ctx)


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'procurement/po_detail.html'
    context_object_name = 'po'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['grns'] = self.object.goods_receipts.all()
        return ctx


class PurchaseOrderMarkSentView(WMSPermissionMixin, View):
    permission_required = 'procurement.change_purchaseorder'

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status == "draft":
            po.status = "sent"
            po.save()
            log_activity(
                request.user,
                f"Marked PO {po.reference} as sent",
                "Procurement",
                request=request
            )
            messages.success(request, f"{po.reference} marked as sent to supplier.")
        return redirect('procurement:po-detail', pk=pk)


# ─── Goods Receipt Views ───────────────────────────────────────

class GoodsReceiptListView(LoginRequiredMixin, ListView):
    model = GoodsReceipt
    template_name = 'procurement/grn_list.html'
    context_object_name = 'receipts'
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related(
            'purchase_order__supplier', 'received_by'
        )


class GoodsReceiptCreateView(WMSPermissionMixin, View):
    permission_required = 'procurement.confirm_goodsreceipt'
    template_name = 'procurement/grn_form.html'

    def get(self, request, po_pk):
        po = get_object_or_404(PurchaseOrder, pk=po_pk)
        if po.status not in ("sent", "partial"):
            messages.error(
                request,
                "You can only receive goods against a sent or partially received PO."
            )
            return redirect('procurement:po-detail', pk=po_pk)

        form = GoodsReceiptForm()
        initial = [
            {
                'purchase_order_item': poi,
                'quantity_received': poi.quantity_pending,
            }
            for poi in po.items.all() if poi.quantity_pending > 0
        ]
        formset = GoodsReceiptItemFormSet(initial=initial)
        for subform, poi_data in zip(formset.forms, initial):
            subform.fields['purchase_order_item'].queryset = po.items.all()
            subform.fields['purchase_order_item'].initial = poi_data['purchase_order_item']

        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'po': po,
        })

    def post(self, request, po_pk):
        po = get_object_or_404(PurchaseOrder, pk=po_pk)
        form = GoodsReceiptForm(request.POST)
        formset = GoodsReceiptItemFormSet(request.POST)
        for subform in formset.forms:
            subform.fields['purchase_order_item'].queryset = po.items.all()

        if form.is_valid() and formset.is_valid():
            grn = form.save(commit=False)
            grn.purchase_order = po
            grn.received_by = request.user
            grn.save()
            formset.instance = grn
            formset.save()
            log_activity(
                request.user,
                f"Created GRN {grn.reference} for PO {po.reference}",
                "Procurement",
                request=request
            )
            messages.success(
                request,
                f"GRN {grn.reference} saved. Confirm it to update stock."
            )
            return redirect('procurement:grn-detail', pk=grn.pk)

        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'po': po,
        })


class GoodsReceiptDetailView(LoginRequiredMixin, DetailView):
    model = GoodsReceipt
    template_name = 'procurement/grn_detail.html'
    context_object_name = 'grn'


class GoodsReceiptConfirmView(WMSPermissionMixin, View):
    permission_required = 'procurement.confirm_goodsreceipt'

    def post(self, request, pk):
        grn = get_object_or_404(GoodsReceipt, pk=pk)
        try:
            confirm_goods_receipt(grn, request.user)
            log_activity(
                request.user,
                f"Confirmed GRN {grn.reference} for PO {grn.purchase_order.reference}",
                "Procurement",
                request=request
            )
            messages.success(
                request,
                f"{grn.reference} confirmed. Stock has been updated."
            )
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('procurement:grn-detail', pk=pk)