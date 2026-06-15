from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/payroll/', include('payroll.urls')),
    path('', include(('payroll.frontend_urls', 'payroll'), namespace='payroll')),
]
