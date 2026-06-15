from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Employee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employee',
    )
    employee_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    hire_date = models.DateField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"


class PayPeriod(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class SalaryComponent(models.Model):
    INCOME = 'income'
    DEDUCTION = 'deduction'
    BENEFIT = 'benefit'

    COMPONENT_TYPES = [
        (INCOME, 'Income'),
        (DEDUCTION, 'Deduction'),
        (BENEFIT, 'Benefit'),
    ]

    employee = models.ForeignKey(Employee, related_name='salary_components', on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPES, default=INCOME)

    def __str__(self):
        return f"{self.employee} - {self.name}"


class PayrollRun(models.Model):
    period = models.ForeignKey(PayPeriod, related_name='payroll_runs', on_delete=models.CASCADE)
    run_date = models.DateTimeField(auto_now_add=True)
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"Payroll {self.period} - {self.run_date.date()}"

    def calculate_totals(self):
        self.total_gross = sum(item.gross_amount for item in self.payroll_items.all())
        self.total_net = sum(item.net_amount for item in self.payroll_items.all())
        self.save()


class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, related_name='payroll_items', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name='payroll_items', on_delete=models.CASCADE)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.employee} - {self.payroll_run}"


class PayrollRecord(models.Model):
    employee_id = models.CharField(max_length=30)
    employee_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    days_worked = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_id', 'employee_name']

    def calculate_salary(self):
        self.salary = self.days_worked * self.rate_per_day
        return self.salary

    def save(self, *args, **kwargs):
        self.calculate_salary()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.employee_name}"
