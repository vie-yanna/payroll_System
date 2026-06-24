from django.urls import path

from .views import (
    DashboardView,
    PayrollHistoryView,
    PayrollLoginView,
    PayrollLogoutView,
    AccountingView,
    PayrollExportView,
)

urlpatterns = [
    path('', PayrollLoginView.as_view(), name='home'),
    path('login/', PayrollLoginView.as_view(), name='login'),
    path('logout/', PayrollLogoutView.as_view(), name='logout'),
    path('accounting/', AccountingView.as_view(), name='accounting'),
    path('accounting/export/', PayrollExportView.as_view(), name='export_payroll'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('history/', PayrollHistoryView.as_view(), name='history'),
]
