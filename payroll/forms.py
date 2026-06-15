from django import forms

from .models import PayrollRecord


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            'employee_id',
            'employee_name',
            'department',
            'days_worked',
            'rate_per_day',
        ]
        labels = {
            'employee_id': 'ID',
            'employee_name': 'Employee Name',
            'days_worked': 'No. of Days',
            'rate_per_day': 'Rate per Day',
        }
        widgets = {
            'employee_id': forms.TextInput(attrs={'placeholder': 'EMPELite-001'}),
            'employee_name': forms.TextInput(attrs={'placeholder': 'Tristan Ramos'}),
            'department': forms.TextInput(attrs={'placeholder': 'IT'}),
            'days_worked': forms.NumberInput(attrs={'step': '0', 'min': '0'}),
            'rate_per_day': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
