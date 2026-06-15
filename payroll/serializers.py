from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Employee, PayPeriod, PayrollRun, PayrollItem, SalaryComponent


User = get_user_model()


class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = ['id', 'employee', 'name', 'amount', 'component_type']


class EmployeeSerializer(serializers.ModelSerializer):
    salary_components = SalaryComponentSerializer(many=True, read_only=True)
    user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='username',
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Employee
        fields = ['id', 'employee_id', 'first_name', 'last_name', 'email', 'hire_date', 'active', 'user', 'salary_components']


class PayPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayPeriod
        fields = ['id', 'name', 'start_date', 'end_date']


class PayrollItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollItem
        fields = ['id', 'payroll_run', 'employee', 'gross_amount', 'total_deductions', 'net_amount']


class PayrollRunSerializer(serializers.ModelSerializer):
    payroll_items = PayrollItemSerializer(many=True, read_only=True)
    period = PayPeriodSerializer(read_only=True)
    period_id = serializers.PrimaryKeyRelatedField(queryset=PayPeriod.objects.all(), source='period', write_only=True)

    class Meta:
        model = PayrollRun
        fields = ['id', 'period', 'period_id', 'run_date', 'total_gross', 'total_net', 'payroll_items']
        read_only_fields = ['run_date', 'total_gross', 'total_net', 'payroll_items']
