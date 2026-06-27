from django import forms
from django.forms import inlineformset_factory
from .models import (
    Project, MaterialRequest, MaterialRequestItem,
    MaterialReturn, MaterialReturnItem
)
from inventory.models import Item, Warehouse
from accounts.models import User


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'code', 'name', 'description', 'project_type',
            'status', 'site_location', 'supervisor',
            'start_date', 'end_date', 'budget'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. PROJ-001'
            }),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
            'project_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'site_location': forms.TextInput(attrs={'class': 'form-control'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supervisor'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name')
        self.fields['supervisor'].required = False


class MaterialRequestForm(forms.ModelForm):
    class Meta:
        model = MaterialRequest
        fields = ['project', 'warehouse', 'notes']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.filter(
            status='active'
        )
        self.fields['project'].required = False
        self.fields['warehouse'].queryset = Warehouse.objects.filter(
            is_active=True
        )


class MaterialRequestItemForm(forms.ModelForm):
    class Meta:
        model = MaterialRequestItem
        fields = ['item', 'quantity_requested', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_requested': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01'
            }),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


MaterialRequestItemFormSet = inlineformset_factory(
    MaterialRequest,
    MaterialRequestItem,
    form=MaterialRequestItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class MaterialReturnForm(forms.ModelForm):
    class Meta:
        model = MaterialReturn
        fields = ['warehouse', 'notes']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['warehouse'].queryset = Warehouse.objects.filter(
            is_active=True
        )


class MaterialReturnItemForm(forms.ModelForm):
    class Meta:
        model = MaterialReturnItem
        fields = ['item', 'quantity_returned', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_returned': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01'
            }),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


MaterialReturnItemFormSet = inlineformset_factory(
    MaterialReturn,
    MaterialReturnItem,
    form=MaterialReturnItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class RejectMaterialRequestForm(forms.Form):
    reason = forms.CharField(
        label="Rejection Reason",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this request is being rejected'
        })
    )