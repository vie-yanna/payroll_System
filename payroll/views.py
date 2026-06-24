from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404, redirect
from .models import Employee
from django.http import JsonResponse

from .forms import PayrollRecordForm
from .models import Employee, PayPeriod, PayrollRun, PayrollItem, PayrollRecord, SalaryComponent
from .serializers import (
    EmployeeSerializer,
    PayPeriodSerializer,
    PayrollRunSerializer,
    PayrollItemSerializer,
    SalaryComponentSerializer,
)


class IsPayrollAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsPayrollRunOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        employee = getattr(request.user, 'employee', None)
        return employee is not None and obj.payroll_items.filter(employee=employee).exists()


class IsPayrollItemOwnerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        employee = getattr(request.user, 'employee', None)
        return employee is not None and obj.employee == employee


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('id')
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]


class PayPeriodViewSet(viewsets.ModelViewSet):
    queryset = PayPeriod.objects.all().order_by('-start_date')
    serializer_class = PayPeriodSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]


class SalaryComponentViewSet(viewsets.ModelViewSet):
    queryset = SalaryComponent.objects.all().select_related('employee')
    serializer_class = SalaryComponentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.all().prefetch_related('payroll_items')
    serializer_class = PayrollRunSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsPayrollRunOwnerOrAdmin()]
        return [permissions.IsAuthenticated(), IsPayrollAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        employee = getattr(user, 'employee', None)
        if not employee:
            return queryset.none()
        return queryset.filter(payroll_items__employee=employee).distinct()

    def perform_create(self, serializer):
        payroll_run = serializer.save()
        self._create_payroll_items(payroll_run)
        payroll_run.calculate_totals()

    def _create_payroll_items(self, payroll_run):
        employees = Employee.objects.filter(active=True).prefetch_related('salary_components')
        for employee in employees:
            income = sum(
                component.amount
                for component in employee.salary_components.all()
                if component.component_type == SalaryComponent.INCOME
            )
            deductions = sum(
                component.amount
                for component in employee.salary_components.all()
                if component.component_type == SalaryComponent.DEDUCTION
            )
            net_amount = Decimal(income) - Decimal(deductions)
            PayrollItem.objects.create(
                payroll_run=payroll_run,
                employee=employee,
                gross_amount=income,
                total_deductions=deductions,
                net_amount=net_amount,
            )


class PayrollItemViewSet(viewsets.ModelViewSet):
    queryset = PayrollItem.objects.all().select_related('employee', 'payroll_run')
    serializer_class = PayrollItemSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated(), IsPayrollItemOwnerOrAdmin()]
        return [permissions.IsAuthenticated(), IsPayrollAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        employee = getattr(user, 'employee', None)
        if not employee:
            return queryset.none()
        return queryset.filter(employee=employee)


class PayrollLoginView(LoginView):
    template_name = 'payroll/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_staff:
            return reverse_lazy('payroll:dashboard')
        return reverse_lazy('payroll:history')


class PayrollLogoutView(LogoutView):
    next_page = reverse_lazy('payroll:login')


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class PayrollHistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'payroll/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_staff:
            payroll_runs = PayrollRun.objects.order_by('-run_date')
        else:
            employee = getattr(user, 'employee', None)
            payroll_runs = PayrollRun.objects.filter(payroll_items__employee=employee).distinct().order_by('-run_date') if employee else PayrollRun.objects.none()
        context.update({
            'payroll_runs': payroll_runs,
            'employee': getattr(user, 'employee', None),
        })
        return context


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/dashboard.html'

    def get_edit_record(self):
        record_id = self.request.GET.get('edit')
        if not record_id:
            return None
        return PayrollRecord.objects.filter(pk=record_id).first()

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')
        instance = PayrollRecord.objects.filter(pk=record_id).first() if record_id else None
        form = PayrollRecordForm(request.POST, instance=instance if action == 'update' else None)

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, selected_record=instance))

        record = form.save(commit=False)
        record.calculate_salary()

        if action == 'compute':
            messages.info(request, 'Salary computed. Click Save to add it or Update to change the selected record.')
            return self.render_to_response(
                self.get_context_data(form=form, selected_record=instance, computed_salary=record.salary)
            )

        if action == 'update':
            if not instance:
                messages.error(request, 'Choose a payroll record to update first.')
                return self.render_to_response(self.get_context_data(form=form))
            record.save()
            messages.success(request, 'Payroll record updated.')
            return redirect('payroll:dashboard')

        record.pk = None
        record.save()
        messages.success(request, 'Payroll record saved.')
        return redirect('payroll:dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totals = PayrollRun.objects.aggregate(
            total_gross=Sum('total_gross'),
            total_net=Sum('total_net'),
        )
        selected_record = kwargs.get('selected_record') or self.get_edit_record()
        form = kwargs.get('form') or PayrollRecordForm(instance=selected_record)
        context.update({
            'employee_count': Employee.objects.filter(active=True).count(),
            'pay_period_count': PayPeriod.objects.count(),
            'payroll_runs': PayrollRun.objects.order_by('-run_date')[:5],
            'payroll_records': PayrollRecord.objects.all(),
            'payroll_form': form,
            'selected_record': selected_record,
            'computed_salary': kwargs.get(
                'computed_salary',
                selected_record.salary if selected_record else None,
            ),
            'total_gross': totals.get('total_gross') or 0,
            'total_net': totals.get('total_net') or 0,
        })
        return context

def employee_list(request):
    employees = Employee.objects.all().values()
    return JsonResponse(list(employees), safe=False)

def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)

    if request.method == "POST":
        employee.is_deleted = True
        employee.save()
        return redirect('employee_list')

    return render(request, 'confirm_delete.html', {'employee': employee})


