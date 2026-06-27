# assets/views.py
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from core.mixins import WMSPermissionMixin
from accounts.views import log_activity

from .models import Asset, AssetCategory, AssetAssignment, MaintenanceRecord
from .forms import (
    AssetForm, AssetCategoryForm,
    AssetAssignmentForm, AssetReturnForm,
    MaintenanceRecordForm,
)


# ─── Asset Category Views ──────────────────────────────────────

class AssetCategoryListView(LoginRequiredMixin, ListView):
    model = AssetCategory
    template_name = 'assets/category_list.html'
    context_object_name = 'categories'


class AssetCategoryCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'assets.add_assetcategory'
    model = AssetCategory
    form_class = AssetCategoryForm
    template_name = 'assets/category_form.html'
    success_url = reverse_lazy('assets:category-list')

    def form_valid(self, form):
        messages.success(self.request, "Category created.")
        return super().form_valid(form)


class AssetCategoryUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'assets.change_assetcategory'
    model = AssetCategory
    form_class = AssetCategoryForm
    template_name = 'assets/category_form.html'
    success_url = reverse_lazy('assets:category-list')

    def form_valid(self, form):
        messages.success(self.request, "Category updated.")
        return super().form_valid(form)


# ─── Asset Views ───────────────────────────────────────────────

class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = 'assets/asset_list.html'
    context_object_name = 'assets'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('category')
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        asset_type = self.request.GET.get('type')

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(asset_number__icontains=q) |
                Q(serial_number__icontains=q) |
                Q(brand__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if asset_type:
            qs = qs.filter(asset_type=asset_type)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['statuses'] = Asset.STATUS_CHOICES
        ctx['asset_types'] = Asset.ASSET_TYPE_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class AssetCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'assets.add_asset'
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        log_activity(
            self.request.user,
            f"Registered asset: {form.instance.asset_number} - {form.instance.name}",
            "Assets",
            request=self.request
        )
        messages.success(
            self.request,
            f"Asset {form.instance.asset_number} registered."
        )
        return super().form_valid(form)


class AssetUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'assets.change_asset'
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset-list')

    def form_valid(self, form):
        log_activity(
            self.request.user,
            f"Updated asset: {form.instance.asset_number} - {form.instance.name}",
            "Assets",
            request=self.request
        )
        messages.success(self.request, "Asset updated.")
        return super().form_valid(form)


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    template_name = 'assets/asset_detail.html'
    context_object_name = 'asset'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['current_assignment'] = self.object.current_assignment
        ctx['assignment_history'] = self.object.assignments.select_related(
            'assigned_to', 'project', 'assigned_by'
        ).order_by('-assigned_at')
        ctx['maintenance_records'] = self.object.maintenance_records.select_related(
            'created_by'
        ).order_by('-scheduled_date')
        ctx['assign_form'] = AssetAssignmentForm()
        ctx['return_form'] = AssetReturnForm()
        return ctx


# ─── Assignment & Return Views ────────────────────────────────

class AssetAssignView(WMSPermissionMixin, View):
    permission_required = 'assets.assign_asset'

    def post(self, request, pk):
        asset = get_object_or_404(Asset, pk=pk)

        if not asset.is_available:
            messages.error(
                request,
                f"{asset.name} is not available for assignment."
            )
            return redirect('assets:asset-detail', pk=pk)

        form = AssetAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.asset = asset
            assignment.assigned_by = request.user
            assignment.save()

            asset.status = "assigned"
            asset.save()

            log_activity(
                request.user,
                f"Assigned asset {asset.asset_number} to {assignment.assigned_to.get_full_name()}",
                "Assets",
                request=request
            )
            messages.success(
                request,
                f"{asset.name} assigned to {assignment.assigned_to.get_full_name()}."
            )
        else:
            messages.error(request, "Please fix the errors below.")

        return redirect('assets:asset-detail', pk=pk)


class AssetReturnView(WMSPermissionMixin, View):
    permission_required = 'assets.return_asset'

    def post(self, request, pk):
        asset = get_object_or_404(Asset, pk=pk)
        assignment = asset.current_assignment

        if not assignment:
            messages.error(request, "This asset has no active assignment.")
            return redirect('assets:asset-detail', pk=pk)

        form = AssetReturnForm(request.POST)
        if form.is_valid():
            assignment.returned_at = timezone.now()
            assignment.return_condition = form.cleaned_data['return_condition']
            assignment.return_notes = form.cleaned_data['return_notes']
            assignment.save()

            asset.condition = form.cleaned_data['return_condition']
            asset.status = (
                "available"
                if form.cleaned_data['return_condition'] != "out_of_service"
                else "out_of_service"
            )
            asset.save()

            log_activity(
                request.user,
                f"Returned asset {asset.asset_number} with condition {asset.condition}",
                "Assets",
                request=request
            )
            messages.success(
                request,
                f"{asset.name} returned and marked as {asset.get_status_display()}."
            )
        else:
            messages.error(request, "Please fix the errors.")

        return redirect('assets:asset-detail', pk=pk)


# ─── Maintenance Views ─────────────────────────────────────────

class MaintenanceListView(LoginRequiredMixin, ListView):
    model = MaintenanceRecord
    template_name = 'assets/maintenance_list.html'
    context_object_name = 'records'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('asset', 'created_by')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = MaintenanceRecord.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')

        today = timezone.now().date()
        ctx['due_soon'] = Asset.objects.filter(
            next_maintenance_date__lte=today + timedelta(days=7),
            next_maintenance_date__isnull=False,
            status__in=('available', 'assigned')
        ).order_by('next_maintenance_date')
        return ctx


class MaintenanceCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'assets.schedule_maintenance'
    model = MaintenanceRecord
    form_class = MaintenanceRecordForm
    template_name = 'assets/maintenance_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['asset'] = get_object_or_404(Asset, pk=self.kwargs['asset_pk'])
        return ctx

    def form_valid(self, form):
        asset = get_object_or_404(Asset, pk=self.kwargs['asset_pk'])
        form.instance.asset = asset
        form.instance.created_by = self.request.user

        if form.cleaned_data.get('next_maintenance_date'):
            asset.next_maintenance_date = form.cleaned_data['next_maintenance_date']

        if form.cleaned_data.get('status') == 'in_progress':
            asset.status = 'under_maintenance'

        asset.save()

        log_activity(
            self.request.user,
            f"Scheduled maintenance for asset {asset.asset_number}",
            "Assets",
            request=self.request
        )
        messages.success(
            self.request,
            f"Maintenance record added for {asset.name}."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('assets:asset-detail', kwargs={
            'pk': self.kwargs['asset_pk']
        })


class MaintenanceUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'assets.schedule_maintenance'
    model = MaintenanceRecord
    form_class = MaintenanceRecordForm
    template_name = 'assets/maintenance_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['asset'] = self.object.asset
        return ctx

    def form_valid(self, form):
        asset = self.object.asset

        if form.cleaned_data.get('status') == 'completed':
            if asset.status == 'under_maintenance':
                asset.status = 'available'
            if form.cleaned_data.get('next_maintenance_date'):
                asset.next_maintenance_date = form.cleaned_data['next_maintenance_date']
            asset.save()

        log_activity(
            self.request.user,
            f"Updated maintenance record for asset {asset.asset_number}",
            "Assets",
            request=self.request
        )
        messages.success(self.request, "Maintenance record updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('assets:asset-detail', kwargs={'pk': self.object.asset.pk})