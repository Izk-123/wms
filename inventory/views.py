# inventory/views.py
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, CreateView, TemplateView, UpdateView, DetailView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.core.exceptions import ValidationError

from core.mixins import WMSPermissionMixin
from accounts.views import log_activity

from .models import Category, Unit, Warehouse, Item, Stock, StockMovement
from .services import receive_stock, issue_stock, transfer_stock, adjust_stock
from .qr_service import generate_qr_and_barcode
from .forms import (
    CategoryForm, UnitForm, WarehouseForm, ItemForm,
    StockReceiveForm, StockIssueForm, StockTransferForm, StockAdjustForm
)


# ─── Category Views ────────────────────────────────────────────

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
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


class CategoryCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'inventory.add_category'
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category-list')

    def form_valid(self, form):
        messages.success(self.request, "Category created successfully.")
        return super().form_valid(form)


class CategoryUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'inventory.change_category'
    model = Category
    form_class = CategoryForm
    template_name = 'inventory/category_form.html'
    success_url = reverse_lazy('inventory:category-list')

    def form_valid(self, form):
        messages.success(self.request, "Category updated successfully.")
        return super().form_valid(form)


# ─── Unit Views ────────────────────────────────────────────────

class UnitListView(LoginRequiredMixin, ListView):
    model = Unit
    template_name = 'inventory/unit_list.html'
    context_object_name = 'units'
    paginate_by = 20


class UnitCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'inventory.add_unit'
    model = Unit
    form_class = UnitForm
    template_name = 'inventory/unit_form.html'
    success_url = reverse_lazy('inventory:unit-list')

    def form_valid(self, form):
        messages.success(self.request, "Unit created successfully.")
        return super().form_valid(form)


class UnitUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'inventory.change_unit'
    model = Unit
    form_class = UnitForm
    template_name = 'inventory/unit_form.html'
    success_url = reverse_lazy('inventory:unit-list')

    def form_valid(self, form):
        messages.success(self.request, "Unit updated successfully.")
        return super().form_valid(form)


# ─── Warehouse Views ───────────────────────────────────────────

class WarehouseListView(LoginRequiredMixin, ListView):
    model = Warehouse
    template_name = 'inventory/warehouse_list.html'
    context_object_name = 'warehouses'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(location__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class WarehouseCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'inventory.add_warehouse'
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'inventory/warehouse_form.html'
    success_url = reverse_lazy('inventory:warehouse-list')

    def form_valid(self, form):
        messages.success(self.request, "Warehouse created successfully.")
        return super().form_valid(form)


class WarehouseUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'inventory.change_warehouse'
    model = Warehouse
    form_class = WarehouseForm
    template_name = 'inventory/warehouse_form.html'
    success_url = reverse_lazy('inventory:warehouse-list')

    def form_valid(self, form):
        messages.success(self.request, "Warehouse updated successfully.")
        return super().form_valid(form)


class WarehouseDetailView(LoginRequiredMixin, DetailView):
    model = Warehouse
    template_name = 'inventory/warehouse_detail.html'
    context_object_name = 'warehouse'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stocks'] = Stock.objects.filter(
            warehouse=self.object
        ).select_related('item', 'item__unit').order_by('item__name')
        return ctx


# ─── Item Views ────────────────────────────────────────────────

class ItemListView(LoginRequiredMixin, ListView):
    model = Item
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('category', 'unit')
        q = self.request.GET.get('q')
        category = self.request.GET.get('category')
        item_type = self.request.GET.get('item_type')

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(sku__icontains=q) |
                Q(description__icontains=q)
            )
        if category:
            qs = qs.filter(category_id=category)
        if item_type:
            qs = qs.filter(item_type=item_type)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['categories'] = Category.objects.all()
        ctx['item_types'] = Item.ITEM_TYPE_CHOICES
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_type'] = self.request.GET.get('item_type', '')
        return ctx


class ItemCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'inventory.add_item'
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('inventory:item-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Generate QR and barcode after save
        try:
            generate_qr_and_barcode(self.object)
        except Exception:
            pass  # Don't block item creation
        log_activity(
            self.request.user,
            f"Created item: {self.object.sku} - {self.object.name}",
            "Inventory",
            request=self.request
        )
        messages.success(
            self.request,
            f"Item '{self.object.name}' created. SKU: {self.object.sku}."
        )
        return response


class ItemUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'inventory.change_item'
    model = Item
    form_class = ItemForm
    template_name = 'inventory/item_form.html'
    success_url = reverse_lazy('inventory:item-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Regenerate QR if SKU or name changed
        try:
            generate_qr_and_barcode(self.object)
        except Exception:
            pass
        log_activity(
            self.request.user,
            f"Updated item: {self.object.sku} - {self.object.name}",
            "Inventory",
            request=self.request
        )
        messages.success(self.request, f"Item '{self.object.name}' updated.")
        return response


class ItemDetailView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['stocks'] = Stock.objects.filter(item=self.object).select_related('warehouse')
        ctx['movements'] = StockMovement.objects.filter(
            item=self.object
        ).select_related('warehouse', 'created_by').order_by('-created_at')[:20]
        ctx['total_stock'] = Stock.objects.filter(
            item=self.object
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return ctx


class RegenerateQRView(WMSPermissionMixin, View):
    permission_required = 'inventory.change_item'

    def post(self, request, pk):
        item = get_object_or_404(Item, pk=pk)
        try:
            generate_qr_and_barcode(item)
            log_activity(
                request.user,
                f"Regenerated QR/barcode for {item.sku}",
                "Inventory",
                request=request
            )
            messages.success(request, f"QR code and barcode regenerated for {item.name}.")
        except Exception as e:
            messages.error(request, f"Failed to generate codes: {str(e)}")
        return redirect('inventory:item-detail', pk=pk)


class ItemLabelView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_label.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_stock'] = Stock.objects.filter(
            item=self.object
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return ctx


class ItemLabelSheetView(LoginRequiredMixin, DetailView):
    model = Item
    template_name = 'inventory/item_label_sheet.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_stock'] = Stock.objects.filter(
            item=self.object
        ).aggregate(total=Sum('quantity'))['total'] or 0
        ctx['label_range'] = range(6)
        return ctx


class QRScannerView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/qr_scanner.html'


class QRLookupView(LoginRequiredMixin, View):
    def get(self, request):
        import json
        sku = request.GET.get('sku', '').strip()

        if not sku:
            raw = request.GET.get('data', '')
            try:
                payload = json.loads(raw)
                sku = payload.get('sku', '')
            except (json.JSONDecodeError, Exception):
                sku = raw.strip()

        if not sku:
            messages.error(request, "No SKU found in QR code.")
            return redirect('inventory:qr-scanner')

        item = Item.objects.filter(sku=sku).first()
        if item:
            return redirect('inventory:item-detail', pk=item.pk)

        messages.error(request, f"No item found with SKU: {sku}")
        return redirect('inventory:qr-scanner')


# ─── Stock Views ───────────────────────────────────────────────

class StockListView(LoginRequiredMixin, ListView):
    model = Stock
    template_name = 'inventory/stock_list.html'
    context_object_name = 'stocks'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'item', 'item__category', 'item__unit', 'warehouse'
        )
        q = self.request.GET.get('q')
        warehouse = self.request.GET.get('warehouse')
        low_stock = self.request.GET.get('low_stock')

        if q:
            qs = qs.filter(
                Q(item__name__icontains=q) |
                Q(item__sku__icontains=q)
            )
        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        if low_stock:
            qs = qs.filter(quantity__lte=F('item__minimum_stock'))

        return qs.order_by('item__name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['warehouses'] = Warehouse.objects.filter(is_active=True)
        ctx['selected_warehouse'] = self.request.GET.get('warehouse', '')
        ctx['low_stock_filter'] = self.request.GET.get('low_stock', '')
        return ctx


class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'item', 'warehouse', 'created_by'
        )
        q = self.request.GET.get('q')
        movement_type = self.request.GET.get('type')

        if q:
            qs = qs.filter(
                Q(item__name__icontains=q) |
                Q(reference__icontains=q)
            )
        if movement_type:
            qs = qs.filter(movement_type=movement_type)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['movement_types'] = StockMovement.MOVEMENT_TYPES
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


# ─── Stock Operation Views ─────────────────────────────────────

class StockReceiveView(WMSPermissionMixin, FormView):
    permission_required = 'inventory.receive_stock'
    template_name = 'inventory/stock_receive.html'
    form_class = StockReceiveForm
    success_url = reverse_lazy('inventory:stock-list')

    def form_valid(self, form):
        try:
            movement = receive_stock(
                item=form.cleaned_data['item'],
                warehouse=form.cleaned_data['warehouse'],
                quantity=form.cleaned_data['quantity'],
                reference=form.cleaned_data['reference'],
                notes=form.cleaned_data['notes'],
                user=self.request.user,
            )
            log_activity(
                self.request.user,
                f"Received {movement.quantity} {movement.item.unit.symbol} "
                f"of {movement.item.name} into {movement.warehouse.name}",
                "Inventory",
                request=self.request
            )
            messages.success(
                self.request,
                f"Successfully received {movement.quantity} "
                f"{movement.item.unit.symbol} of {movement.item.name}."
            )
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)


class StockIssueView(WMSPermissionMixin, FormView):
    permission_required = 'inventory.issue_stock'
    template_name = 'inventory/stock_issue.html'
    form_class = StockIssueForm
    success_url = reverse_lazy('inventory:stock-list')

    def form_valid(self, form):
        try:
            movement = issue_stock(
                item=form.cleaned_data['item'],
                warehouse=form.cleaned_data['warehouse'],
                quantity=form.cleaned_data['quantity'],
                reference=form.cleaned_data['reference'],
                notes=form.cleaned_data['notes'],
                user=self.request.user,
            )
            log_activity(
                self.request.user,
                f"Issued {movement.quantity} {movement.item.unit.symbol} "
                f"of {movement.item.name} from {movement.warehouse.name}",
                "Inventory",
                request=self.request
            )
            messages.success(
                self.request,
                f"Successfully issued {movement.quantity} "
                f"{movement.item.unit.symbol} of {movement.item.name}."
            )
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)


class StockTransferView(WMSPermissionMixin, FormView):
    permission_required = 'inventory.transfer_stock'
    template_name = 'inventory/stock_transfer.html'
    form_class = StockTransferForm
    success_url = reverse_lazy('inventory:stock-list')

    def form_valid(self, form):
        try:
            movement = transfer_stock(
                item=form.cleaned_data['item'],
                from_warehouse=form.cleaned_data['from_warehouse'],
                to_warehouse=form.cleaned_data['to_warehouse'],
                quantity=form.cleaned_data['quantity'],
                reference=form.cleaned_data['reference'],
                notes=form.cleaned_data['notes'],
                user=self.request.user,
            )
            log_activity(
                self.request.user,
                f"Transferred {movement.quantity} {movement.item.unit.symbol} "
                f"of {movement.item.name} from {form.cleaned_data['from_warehouse'].name} "
                f"to {form.cleaned_data['to_warehouse'].name}",
                "Inventory",
                request=self.request
            )
            messages.success(
                self.request,
                f"Successfully transferred {movement.quantity} "
                f"{movement.item.unit.symbol} of {movement.item.name}."
            )
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)


class StockAdjustView(WMSPermissionMixin, FormView):
    permission_required = 'inventory.adjust_stock'
    template_name = 'inventory/stock_adjust.html'
    form_class = StockAdjustForm
    success_url = reverse_lazy('inventory:stock-list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        item_id = self.request.GET.get('item')
        warehouse_id = self.request.GET.get('warehouse')
        ctx['current_stock'] = None
        if item_id and warehouse_id:
            ctx['current_stock'] = Stock.objects.filter(
                item_id=item_id,
                warehouse_id=warehouse_id
            ).first()
        return ctx

    def form_valid(self, form):
        try:
            movement = adjust_stock(
                item=form.cleaned_data['item'],
                warehouse=form.cleaned_data['warehouse'],
                new_quantity=form.cleaned_data['new_quantity'],
                reason=form.cleaned_data['reason'],
                user=self.request.user,
            )
            log_activity(
                self.request.user,
                f"Adjusted stock for {movement.item.name} in {movement.warehouse.name} "
                f"to {form.cleaned_data['new_quantity']}",
                "Inventory",
                request=self.request
            )
            messages.success(
                self.request,
                f"Stock adjusted for {movement.item.name} "
                f"in {movement.warehouse.name}."
            )
            return super().form_valid(form)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)