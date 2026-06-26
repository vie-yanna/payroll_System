from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect

from .excel_export import build_xlsx
from .forms import PayrollRecordForm, DeductionOverrideForm, DeductionConfigForm
from .models import Employee, PayPeriod, PayrollRun, PayrollItem, PayrollRecord, SalaryComponent, DeductionConfig
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
            records = PayrollRecord.objects.filter(is_deleted=False).order_by('-cutoff_end')
        else:
            employee = getattr(user, 'employee', None)
            if employee:
                records = PayrollRecord.objects.filter(
                    is_deleted=False,
                    employee_id=employee.employee_id,
                ).order_by('-cutoff_end')
            else:
                records = PayrollRecord.objects.none()

        context.update({
            'records': records,
            'employee': getattr(user, 'employee', None),
        })
        return context


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        totals = PayrollRecord.objects.filter(is_deleted=False).aggregate(
            total_gross=Sum('gross_pay'),
            total_net=Sum('net_pay'),
            total_deductions=Sum('total_deductions'),
        )
        context.update({
            'employee_count': Employee.objects.filter(active=True).count(),
            'pay_period_count': PayPeriod.objects.count(),
            'payroll_records': PayrollRecord.objects.filter(is_deleted=False),
            'total_gross': totals.get('total_gross') or 0,
            'total_net': totals.get('total_net') or 0,
            'total_deductions': totals.get('total_deductions') or 0,
        })
        return context


class AccountingView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/accounting.html'

    def get_edit_record(self):
        record_id = self.request.GET.get('edit')
        if not record_id:
            return None
        return PayrollRecord.objects.filter(pk=record_id).first()

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')
        instance = PayrollRecord.objects.filter(pk=record_id).first() if record_id else None

        if action in {'mark_paid', 'mark_unpaid', 'delete'}:
            if not instance:
                messages.error(request, 'Choose a payroll record first.')
                return redirect('payroll:accounting')

            if action == 'mark_paid':
                instance.is_paid = True
                instance.paid_at = timezone.now()
                instance.save(update_fields=['is_paid', 'paid_at'])
                messages.success(request, 'Payroll marked as paid.')
            elif action == 'mark_unpaid':
                instance.is_paid = False
                instance.paid_at = None
                instance.save(update_fields=['is_paid', 'paid_at'])
                messages.success(request, 'Payroll marked as unpaid.')
            else:
                instance.is_deleted = True
                instance.save(update_fields=['is_deleted'])
                messages.success(request, 'Payroll record deleted.')
            return redirect('payroll:accounting')

        form = PayrollRecordForm(request.POST, instance=instance if action == 'update' else None)

        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, selected_record=instance))

        record = form.save(commit=False)

        if action == 'compute':
            record.calculate_salary()   # always auto, no override branch needed
            messages.info(request, 'Salary computed. Click Save to add or Update to change.')
            return self.render_to_response(
                self.get_context_data(form=form, selected_record=instance, computed_record=record)
            )

        if action == 'update':
            if not instance:
                messages.error(request, 'Choose a payroll record to update first.')
                return self.render_to_response(self.get_context_data(form=form))
            record.save()
            messages.success(request, 'Payroll record updated.')
            return redirect('payroll:accounting')

        record.pk = None
        record.save()
        messages.success(request, 'Payroll record saved.')
        return redirect('payroll:accounting')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_record = kwargs.get('selected_record') or self.get_edit_record()
        form = kwargs.get('form') or PayrollRecordForm(instance=selected_record)
        computed_record = kwargs.get('computed_record') or selected_record
        context.update({
            'payroll_records': PayrollRecord.objects.filter(is_deleted=False),
            'payroll_form': form,
            'selected_record': selected_record,
            'computed_record': computed_record,
        })
        return context


class PayrollExportView(StaffRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        records = PayrollRecord.objects.filter(is_deleted=False)
        rows = [[
            'Cutoff Start',
            'Cutoff End',
            'Employee ID',
            'Employee Name',
            'Department',
            'Cutoff Working Days',
            'Absent Days',
            'Paid Days',
            'Rate Per Day',
            'Gross Pay',
            'Absent Deduction',
            'SSS',
            'PhilHealth',
            'Pag-IBIG',
            'Withholding Tax',
            'Total Deductions',
            'Net Pay',
            'Paid Status',
            'Paid At',
        ]]

        for record in records:
            rows.append([
                record.cutoff_start,
                record.cutoff_end,
                record.employee_id,
                record.employee_name,
                record.department,
                record.total_cutoff_days,
                record.absent_days,
                record.days_worked,
                record.rate_per_day,
                record.gross_pay,
                record.absent_deduction,
                record.sss_deduction,
                record.philhealth_deduction,
                record.pagibig_deduction,
                record.withholding_tax,
                record.total_deductions,
                record.net_pay,
                'Paid' if record.is_paid else 'Unpaid',
                timezone.localtime(record.paid_at).replace(tzinfo=None) if record.paid_at else '',
            ])

        response = HttpResponse(
            build_xlsx(rows),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="payroll-records.xlsx"'
        return response

def employee_list(request):
    employees = Employee.objects.all().values()
    return JsonResponse(list(employees), safe=False)

def delete_employee(request, id):
    employee = get_object_or_404(Employee, id=id)

    if request.method == "POST":
        employee.active = False
        employee.save()
        return redirect('payroll:dashboard')

    return redirect('payroll:dashboard')

class DeductionOverrideView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/deduction.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['records'] = PayrollRecord.objects.filter(is_deleted=False).order_by('-cutoff_end')
        return context


class DeductionEditView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/deduction_edit.html'

    def get_record(self, pk):
        return get_object_or_404(PayrollRecord, pk=pk, is_deleted=False)

    def get(self, request, pk, *args, **kwargs):
        record = self.get_record(pk)
        form = DeductionOverrideForm(instance=record)
        return self.render_to_response(self.get_context_data(form=form, record=record))

    def post(self, request, pk, *args, **kwargs):
        record = self.get_record(pk)
        form = DeductionOverrideForm(request.POST, instance=record)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.override_calculations = True   # always lock it when editing manually
            updated.recalculate_totals()
            updated.save()
            messages.success(request, f'Deductions updated for {record.employee_name}.')
            return redirect('payroll:deductions')
        return self.render_to_response(self.get_context_data(form=form, record=record))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class DeductionConfigView(StaffRequiredMixin, TemplateView):
    template_name = 'payroll/deduction_config.html'

    def get(self, request, *args, **kwargs):
        config = DeductionConfig.get()
        form = DeductionConfigForm(instance=config)
        return self.render_to_response(self.get_context_data(form=form, config=config))

    def post(self, request, *args, **kwargs):
        config = DeductionConfig.get()
        form = DeductionConfigForm(request.POST, instance=config)
        if form.is_valid():
            cfg = form.save(commit=False)
            cfg.updated_by = request.user
            cfg.save()
            messages.success(request, 'Deduction rates updated. All future computations will use the new rates.')
            return redirect('payroll:deduction_config')
        return self.render_to_response(self.get_context_data(form=form, config=config))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form']   = kwargs.get('form')
        context['config'] = kwargs.get('config')
        return context
    
class EmployeeUserLinkView(StaffRequiredMixin, TemplateView):
    """
    Lets admin create a login account for an employee, or link an existing one.
    """
    template_name = 'payroll/employee_link.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.filter(active=True).order_by('last_name')
        return context

    def post(self, request, *args, **kwargs):
        employee_pk = request.POST.get('employee_pk')
        action = request.POST.get('action')
        employee = get_object_or_404(Employee, pk=employee_pk)

        if action == 'create':
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()

            if not username or not password:
                messages.error(request, 'Username and password are required.')
                return redirect('payroll:employee_link')

            User = get_user_model()
            if User.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" is already taken.')
                return redirect('payroll:employee_link')

            user = User.objects.create_user(username=username, password=password)
            employee.user = user
            employee.save()
            messages.success(request, f'Account created and linked to {employee.first_name} {employee.last_name}.')

        elif action == 'unlink':
            employee.user = None
            employee.save()
            messages.success(request, f'Account unlinked from {employee.first_name} {employee.last_name}.')

        return redirect('payroll:employee_link')