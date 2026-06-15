from django.urls import path

from .views import (
    DashboardView,
    PayrollHistoryView,
    PayrollLoginView,
    PayrollLogoutView,
)

urlpatterns = [
    path('', PayrollLoginView.as_view(), name='home'),
    path('login/', PayrollLoginView.as_view(), name='login'),
    path('logout/', PayrollLogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('history/', PayrollHistoryView.as_view(), name='history'),
]
