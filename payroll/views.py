from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Employee, PayPeriod, PayrollRun, PayrollItem, SalaryComponent
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
    queryset = Employee.objects.all().order_by('employee_id')
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totals = PayrollRun.objects.aggregate(
            total_gross=Sum('total_gross'),
            total_net=Sum('total_net'),
        )
        context.update({
            'employee_count': Employee.objects.filter(active=True).count(),
            'pay_period_count': PayPeriod.objects.count(),
            'payroll_runs': PayrollRun.objects.order_by('-run_date')[:5],
            'total_gross': totals.get('total_gross') or 0,
            'total_net': totals.get('total_net') or 0,
        })
        return context
