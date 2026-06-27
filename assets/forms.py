from django import forms
from django.utils import timezone
from .models import Asset, AssetCategory, AssetAssignment, MaintenanceRecord
from accounts.models import User
from operations.models import Project


class AssetCategoryForm(forms.ModelForm):
    class Meta:
        model = AssetCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Power Tools'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'asset_number', 'name', 'description',
            'asset_type', 'category', 'brand', 'model_number',
            'serial_number', 'purchase_date', 'purchase_cost',
            'condition', 'status', 'location',
            'requires_calibration', 'next_calibration_date',
            'next_maintenance_date', 'notes',
        ]
        widgets = {
            'asset_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. AST-001'
            }),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'purchase_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'requires_calibration': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'next_calibration_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'next_maintenance_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }


class AssetAssignmentForm(forms.ModelForm):
    class Meta:
        model = AssetAssignment
        fields = [
            'assigned_to', 'project',
            'expected_return_date', 'notes'
        ]
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name')
        self.fields['project'].queryset = Project.objects.filter(
            status='active'
        )
        self.fields['project'].required = False
        self.fields['expected_return_date'].required = False


class AssetReturnForm(forms.Form):
    return_condition = forms.ChoiceField(
        choices=Asset.CONDITION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    return_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any damage, missing parts, or observations'
        })
    )


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = [
            'maintenance_type', 'status', 'scheduled_date',
            'completed_date', 'performed_by', 'cost',
            'description', 'findings', 'next_maintenance_date',
        ]
        widgets = {
            'maintenance_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'completed_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'performed_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Name or company'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
            'findings': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
            'next_maintenance_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
        }