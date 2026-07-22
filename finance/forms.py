from django import forms
from .models import Account, BankAccount, Budget, BudgetLine, Expense, FiscalPeriod, SupplierBill

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'parent', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SupplierBillForm(forms.ModelForm):
    class Meta:
        model = SupplierBill
        fields = ['supplier', 'purchase_order', 'amount', 'due_date', 'description', 'notes']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'purchase_order': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['purchase_order'].required = False
        self.fields['due_date'].required = False


class OpenDrawerForm(forms.Form):
    opening_balance = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control-wms', 'step': '0.01'})
    )


class CloseDrawerForm(forms.Form):
    closing_balance = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control-wms', 'step': '0.01'})
    )
    
# ─── Bank Reconciliation Forms ────────────────────────────────────

class BankStatementUploadForm(forms.Form):
    account = forms.ModelChoiceField(queryset=BankAccount.objects.filter(is_active=True))
    statement_file = forms.FileField(
        help_text="Upload CSV file with columns: date, reference, description, amount"
    )


class BankReconciliationForm(forms.Form):
    opening_balance = forms.DecimalField(max_digits=15, decimal_places=2)
    closing_balance = forms.DecimalField(max_digits=15, decimal_places=2)


# ─── Budget Forms ──────────────────────────────────────────────────

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['department', 'fiscal_year', 'amount', 'notes']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'fiscal_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2000}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ['category', 'amount', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# ─── Fiscal Period Form ────────────────────────────────────────────

class FiscalPeriodForm(forms.ModelForm):
    class Meta:
        model = FiscalPeriod
        fields = ['name', 'start_date', 'end_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }