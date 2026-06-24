from django.contrib import admin
from .models import Employee, PayPeriod, PayrollRun, PayrollItem, PayrollRecord, SalaryComponent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'employee_id', 'email', 'hire_date', 'active', 'user')
    search_fields = ('first_name', 'last_name', 'employee_id', 'email', 'user__username')
    raw_id_fields = ('user',)

@admin.register(PayPeriod)
class PayPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date')

class PayrollItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 0

@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('period', 'run_date', 'total_gross', 'total_net')
    inlines = [PayrollItemInline]

@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'name', 'amount', 'component_type')
    list_filter = ('component_type',)


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = (
        'employee_id',
        'employee_name',
        'department',
        'cutoff_start',
        'cutoff_end',
        'gross_pay',
        'total_deductions',
        'net_pay',
        'is_paid',
        'paid_at',
    )
    list_filter = ('department', 'cutoff_start', 'cutoff_end', 'is_paid')
    search_fields = ('employee_id', 'employee_name', 'department')
