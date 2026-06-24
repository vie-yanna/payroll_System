from django import forms

from .models import PayrollRecord


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
            'employee_name': forms.TextInput(attrs={'placeholder': 'Tristan Ramos'}),
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
