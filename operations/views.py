# operations/views.py
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q

from core.mixins import WMSPermissionMixin
from accounts.views import log_activity

from .models import Project, MaterialRequest, MaterialReturn
from .forms import (
    ProjectForm,
    MaterialRequestForm, MaterialRequestItemFormSet,
    MaterialReturnForm, MaterialReturnItemFormSet,
    RejectMaterialRequestForm,
)
from .services import (
    submit_material_request, approve_material_request,
    reject_material_request, issue_materials,
    process_material_return,
)


# ─── Project Views ─────────────────────────────────────────────

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'operations/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('supervisor')
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        project_type = self.request.GET.get('type')

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(code__icontains=q) |
                Q(site_location__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if project_type:
            qs = qs.filter(project_type=project_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['statuses'] = Project.STATUS_CHOICES
        ctx['project_types'] = Project.PROJECT_TYPE_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        ctx['selected_type'] = self.request.GET.get('type', '')
        return ctx


class ProjectCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'operations.add_project'
    model = Project
    form_class = ProjectForm
    template_name = 'operations/project_form.html'
    success_url = reverse_lazy('operations:project-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        log_activity(
            self.request.user,
            f"Created project: {form.instance.code} - {form.instance.name}",
            "Operations",
            request=self.request
        )
        messages.success(
            self.request,
            f"Project {form.instance.code} created successfully."
        )
        return super().form_valid(form)


class ProjectUpdateView(WMSPermissionMixin, UpdateView):
    permission_required = 'operations.change_project'
    model = Project
    form_class = ProjectForm
    template_name = 'operations/project_form.html'
    success_url = reverse_lazy('operations:project-list')

    def form_valid(self, form):
        log_activity(
            self.request.user,
            f"Updated project: {form.instance.code} - {form.instance.name}",
            "Operations",
            request=self.request
        )
        messages.success(self.request, "Project updated successfully.")
        return super().form_valid(form)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'operations/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['material_requests'] = self.object.material_requests.select_related(
            'requested_by'
        ).order_by('-created_at')[:20]
        ctx['total_cost'] = self.object.total_material_cost
        return ctx


# ─── Material Request Views ────────────────────────────────────

class MaterialRequestListView(LoginRequiredMixin, ListView):
    model = MaterialRequest
    template_name = 'operations/mr_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related(
            'requested_by', 'project', 'warehouse'
        )
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = MaterialRequest.STATUS_CHOICES
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class MaterialRequestCreateView(WMSPermissionMixin, CreateView):
    permission_required = 'operations.add_materialrequest'
    model = MaterialRequest
    form_class = MaterialRequestForm
    template_name = 'operations/mr_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx['formset'] = MaterialRequestItemFormSet(self.request.POST)
        else:
            ctx['formset'] = MaterialRequestItemFormSet()
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
                f"Created MR {self.object.reference}",
                "Operations",
                request=self.request
            )
            messages.success(
                self.request,
                f"Material Request {self.object.reference} created."
            )
            return redirect('operations:mr-detail', pk=self.object.pk)
        return self.render_to_response(ctx)


class MaterialRequestDetailView(LoginRequiredMixin, DetailView):
    model = MaterialRequest
    template_name = 'operations/mr_detail.html'
    context_object_name = 'mr'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['reject_form'] = RejectMaterialRequestForm()
        ctx['returns'] = self.object.returns.all()
        return ctx


class MaterialRequestActionView(WMSPermissionMixin, View):
    permission_required = 'operations.approve_materialrequest'

    def post(self, request, pk, action):
        mr = get_object_or_404(MaterialRequest, pk=pk)
        try:
            if action == "submit":
                submit_material_request(mr, request.user)
                log_activity(
                    request.user,
                    f"Submitted MR {mr.reference} for approval",
                    "Operations",
                    request=request
                )
                messages.success(
                    request,
                    f"{mr.reference} submitted for approval."
                )

            elif action == "approve":
                approve_material_request(mr, request.user)
                log_activity(
                    request.user,
                    f"Approved MR {mr.reference}",
                    "Operations",
                    request=request
                )
                messages.success(request, f"{mr.reference} approved.")

            elif action == "reject":
                form = RejectMaterialRequestForm(request.POST)
                if form.is_valid():
                    reject_material_request(
                        mr, request.user,
                        form.cleaned_data['reason']
                    )
                    log_activity(
                        request.user,
                        f"Rejected MR {mr.reference}",
                        "Operations",
                        request=request
                    )
                    messages.success(request, f"{mr.reference} rejected.")
                else:
                    messages.error(request, "Please provide a rejection reason.")

            elif action == "issue":
                issue_materials(mr, request.user)
                log_activity(
                    request.user,
                    f"Issued materials for MR {mr.reference}",
                    "Operations",
                    request=request
                )
                messages.success(
                    request,
                    f"Materials issued for {mr.reference}. Stock updated."
                )
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect('operations:mr-detail', pk=pk)


# ─── Material Return Views ─────────────────────────────────────

class MaterialReturnCreateView(WMSPermissionMixin, View):
    permission_required = 'operations.add_materialrequest'
    template_name = 'operations/return_form.html'

    def get(self, request, mr_pk):
        mr = get_object_or_404(MaterialRequest, pk=mr_pk)
        if mr.status not in ("issued", "partially_issued"):
            messages.error(
                request,
                "Returns can only be made against issued requests."
            )
            return redirect('operations:mr-detail', pk=mr_pk)

        form = MaterialReturnForm(initial={'warehouse': mr.warehouse})
        initial = [
            {'item': item.item, 'quantity_returned': 0}
            for item in mr.items.all()
            if item.quantity_issued > 0
        ]
        formset = MaterialReturnItemFormSet(initial=initial)
        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'mr': mr,
        })

    def post(self, request, mr_pk):
        mr = get_object_or_404(MaterialRequest, pk=mr_pk)
        form = MaterialReturnForm(request.POST)
        formset = MaterialReturnItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            material_return = form.save(commit=False)
            material_return.material_request = mr
            material_return.returned_by = request.user
            material_return.save()
            formset.instance = material_return
            formset.save()

            try:
                process_material_return(material_return, request.user)
                log_activity(
                    request.user,
                    f"Returned materials via {material_return.reference}",
                    "Operations",
                    request=request
                )
                messages.success(
                    request,
                    f"{material_return.reference} processed. Items returned to stock."
                )
                return redirect('operations:mr-detail', pk=mr_pk)
            except ValidationError as e:
                material_return.delete()
                messages.error(request, str(e))

        return render(request, self.template_name, {
            'form': form,
            'formset': formset,
            'mr': mr,
        })