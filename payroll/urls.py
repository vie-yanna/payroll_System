from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    EmployeeViewSet,
    PayPeriodViewSet,
    PayrollRunViewSet,
    PayrollItemViewSet,
    SalaryComponentViewSet,
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'periods', PayPeriodViewSet, basename='payperiod')
router.register(r'salary-components', SalaryComponentViewSet, basename='salarycomponent')
router.register(r'payroll-runs', PayrollRunViewSet, basename='payrollrun')
router.register(r'payroll-items', PayrollItemViewSet, basename='payrollitem')

urlpatterns = [
    path('', include(router.urls)),
    path('employees-list/', views.employee_list, name='employee_list'),
    path('employees/delete/<int:id>/', views.delete_employee, name='delete_employee'),
]
