from django import forms
from django.forms import inlineformset_factory
from .models import (
    Supplier, PurchaseRequest, PurchaseRequestItem,
    PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem
)
from inventory.models import Item, Warehouse


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'email',
            'phone', 'address', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Reason for request or additional notes'
            }),
        }


class PurchaseRequestItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequestItem
        fields = ['item', 'quantity', 'estimated_unit_cost', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01'
            }),
            'estimated_unit_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


PurchaseRequestItemFormSet = inlineformset_factory(
    PurchaseRequest,
    PurchaseRequestItem,
    form=PurchaseRequestItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'purchase_request', 'delivery_warehouse',
            'expected_delivery', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'purchase_request': forms.Select(attrs={'class': 'form-select'}),
            'delivery_warehouse': forms.Select(attrs={'class': 'form-select'}),
            'expected_delivery': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved PRs
        self.fields['purchase_request'].queryset = PurchaseRequest.objects.filter(
            status="approved"
        )
        self.fields['purchase_request'].required = False


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['item', 'quantity_ordered', 'unit_cost', 'notes']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_ordered': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01'
            }),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=3,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2
            }),
        }


class GoodsReceiptItemForm(forms.ModelForm):
    class Meta:
        model = GoodsReceiptItem
        fields = ['purchase_order_item', 'quantity_received', 'notes']
        widgets = {
            'purchase_order_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity_received': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0'
            }),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


GoodsReceiptItemFormSet = inlineformset_factory(
    GoodsReceipt,
    GoodsReceiptItem,
    form=GoodsReceiptItemForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=False,
)


class RejectRequestForm(forms.Form):
    reason = forms.CharField(
        label="Rejection Reason",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this request is being rejected'
        })
    )