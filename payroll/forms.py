from django import forms

from .models import PayrollRecord, DeductionConfig


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            'employee_id',
            'employee_name',
            'department',
            'cutoff_start',
            'cutoff_end',
            'total_cutoff_days',
            'absent_days',
            'rate_per_day',
        ]
        labels = {
            'employee_id': 'ID',
            'employee_name': 'Employee Name',
            'cutoff_start': 'Cutoff Start',
            'cutoff_end': 'Cutoff End',
            'total_cutoff_days': 'Cutoff Working Days',
            'absent_days': 'Absent Days',
            'rate_per_day': 'Rate per Day',
        }
        widgets = {
            'employee_id': forms.TextInput(attrs={'placeholder': 'EMPELite-001'}),
            'employee_name': forms.TextInput(attrs={'placeholder': 'John Doe'}),
            'department': forms.TextInput(attrs={'placeholder': 'IT'}),
            'cutoff_start': forms.DateInput(attrs={'type': 'date'}),
            'cutoff_end': forms.DateInput(attrs={'type': 'date'}),
            'total_cutoff_days': forms.NumberInput(attrs={'step': '0.5', 'min': '0'}),
            'absent_days': forms.NumberInput(attrs={'step': '0.5', 'min': '0'}),
            'rate_per_day': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        cutoff_start = cleaned_data.get('cutoff_start')
        cutoff_end = cleaned_data.get('cutoff_end')
        total_cutoff_days = cleaned_data.get('total_cutoff_days') or 0
        absent_days = cleaned_data.get('absent_days') or 0

        if cutoff_start and cutoff_end and cutoff_end < cutoff_start:
            self.add_error('cutoff_end', 'Cutoff end cannot be earlier than cutoff start.')

        if absent_days > total_cutoff_days:
            self.add_error('absent_days', 'Absent days cannot exceed cutoff working days.')

        return cleaned_data
    
class DeductionOverrideForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = [
            'sss_deduction',
            'philhealth_deduction',
            'pagibig_deduction',
            'withholding_tax',
            'override_calculations',
        ]
        labels = {
            'sss_deduction': 'SSS',
            'philhealth_deduction': 'PhilHealth',
            'pagibig_deduction': 'Pag-IBIG',
            'withholding_tax': 'Withholding Tax',
        }
        widgets = {
            'sss_deduction': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'philhealth_deduction': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'pagibig_deduction': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'withholding_tax': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        for field in ['sss_deduction', 'philhealth_deduction', 'pagibig_deduction', 'withholding_tax']:
            value = cleaned_data.get(field)
            if value is not None and value < 0:
                self.add_error(field, 'Deduction cannot be negative.')
        return cleaned_data

class DeductionConfigForm(forms.ModelForm):
    class Meta:
        model = DeductionConfig
        fields = [
            'sss_employee_rate', 'sss_monthly_min', 'sss_monthly_max',
            'philhealth_employee_rate', 'philhealth_monthly_min', 'philhealth_monthly_max',
            'pagibig_monthly_max', 'pagibig_low_rate', 'pagibig_standard_rate', 'pagibig_low_rate_limit',
        ]
        labels = {
            'sss_employee_rate':        'SSS Employee Rate',
            'sss_monthly_min':          'SSS Monthly Floor',
            'sss_monthly_max':          'SSS Monthly Ceiling',
            'philhealth_employee_rate': 'PhilHealth Employee Rate',
            'philhealth_monthly_min':   'PhilHealth Monthly Floor',
            'philhealth_monthly_max':   'PhilHealth Monthly Ceiling',
            'pagibig_monthly_max':      'Pag-IBIG Monthly Ceiling',
            'pagibig_low_rate':         'Pag-IBIG Low Rate',
            'pagibig_standard_rate':    'Pag-IBIG Standard Rate',
            'pagibig_low_rate_limit':   'Pag-IBIG Low Rate Limit',
        }
        widgets = {f: forms.NumberInput(attrs={'step': '0.0001', 'min': '0'})
                   for f in ['sss_employee_rate', 'philhealth_employee_rate',
                              'pagibig_low_rate', 'pagibig_standard_rate']}