from django.urls import path

from .views import (
    DashboardView,
    PayrollHistoryView,
    PayrollLoginView,
    PayrollLogoutView,
    AccountingView,
    PayrollExportView,
    DeductionOverrideView,
    DeductionEditView,
    DeductionConfigView,
    EmployeeUserLinkView,
)

urlpatterns = [
    path('', PayrollLoginView.as_view(), name='home'),
    path('login/', PayrollLoginView.as_view(), name='login'),
    path('logout/', PayrollLogoutView.as_view(), name='logout'),
    path('accounting/', AccountingView.as_view(), name='accounting'),
    path('accounting/export/', PayrollExportView.as_view(), name='export_payroll'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('history/', PayrollHistoryView.as_view(), name='history'),
    path('deductions/', DeductionOverrideView.as_view(), name='deductions'),
    path('deductions/<int:pk>/edit/', DeductionEditView.as_view(), name='edit_deduction'),
    path('deductions/config/', DeductionConfigView.as_view(), name='deduction_config'),
    path('employees/accounts/', EmployeeUserLinkView.as_view(), name='employee_link'),
]
