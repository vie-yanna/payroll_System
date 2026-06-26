from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from decimal import Decimal


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

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
        self.total_gross = sum(
            (item.gross_amount for item in self.payroll_items.all()),
            Decimal('0.00')
        )
        self.total_net = sum(
            (item.net_amount for item in self.payroll_items.all()),
            Decimal('0.00')
        )
        self.save()


class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, related_name='payroll_items', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name='payroll_items', on_delete=models.CASCADE)

    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def calculate_net(self):
        self.net_amount = self.gross_amount - self.total_deductions
        return self.net_amount

    def save(self, *args, **kwargs):
        self.calculate_net()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.payroll_run}"


class PayrollRecord(models.Model):
    employee_link = models.ForeignKey('Employee', null=True, blank=True, on_delete=models.SET_NULL, related_name='payroll_records', help_text='Link to the Employee record for auto-filling name and ID.',)
    employee_id = models.CharField(max_length=30)
    employee_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    cutoff_start = models.DateField(null=True, blank=True)
    cutoff_end = models.DateField(null=True, blank=True)
    total_cutoff_days = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    absent_days = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    days_worked = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    absent_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sss_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    philhealth_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pagibig_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    withholding_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    override_calculations = models.BooleanField(
        default=False,
        help_text='If checked, automatic salary computation is skipped and deductions can be set manually.'
    )

    class Meta:
        ordering = ['-cutoff_end', 'employee_id', 'employee_name']

    def calculate_salary(self):
        from .payroll_calculator import calculate_cutoff_pay

        total_cutoff_days = self.total_cutoff_days or self.days_worked
        values = calculate_cutoff_pay(
            total_cutoff_days=total_cutoff_days,
            absent_days=self.absent_days,
            rate_per_day=self.rate_per_day,
        )
        for field, value in values.items():
            setattr(self, field, value)
        return self.salary

    def recalculate_totals(self):
        """Recompute totals from manually set deduction fields."""
        from .payroll_calculator import money, calculate_cutoff_pay
        from decimal import Decimal

        total_cutoff_days = self.total_cutoff_days or self.days_worked
        absences = self.absent_days or 0
        rate = self.rate_per_day or 0

        paid_days = max(Decimal(str(total_cutoff_days)) - Decimal(str(absences)), Decimal('0'))
        self.gross_pay = money(Decimal(str(total_cutoff_days)) * Decimal(str(rate)))
        self.absent_deduction = money(Decimal(str(absences)) * Decimal(str(rate)))
        self.days_worked = paid_days
        self.salary = money(paid_days * Decimal(str(rate)))

        # Use manually entered deductions as-is
        statutory = (
            Decimal(str(self.sss_deduction or 0)) +
            Decimal(str(self.philhealth_deduction or 0)) +
            Decimal(str(self.pagibig_deduction or 0)) +
            Decimal(str(self.withholding_tax or 0))
        )
        self.total_deductions = money(self.absent_deduction + Decimal(str(statutory)))
        self.net_pay = money(self.gross_pay - self.total_deductions)

    def save(self, *args, **kwargs):
        if self.employee_link:
            if not self.employee_name:
                self.employee_name = (
                    f"{self.employee_link.first_name} {self.employee_link.last_name}"
                )
            if not self.employee_id:
                self.employee_id = self.employee_link.employee_id
 
        if self.override_calculations:
            self.recalculate_totals()
        else:
            self.calculate_salary()
 
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f"{self.employee_id} - {self.employee_name}"
    
class DeductionConfig(models.Model):
    """
    Stores the current statutory deduction rates and limits.
    Only one active row should exist at a time — use DeductionConfig.get() to fetch it.
    """
    sss_employee_rate       = models.DecimalField(max_digits=6,  decimal_places=4, default='0.0500')
    sss_monthly_min         = models.DecimalField(max_digits=10, decimal_places=2, default='5000.00')
    sss_monthly_max         = models.DecimalField(max_digits=10, decimal_places=2, default='35000.00')

    philhealth_employee_rate = models.DecimalField(max_digits=6,  decimal_places=4, default='0.0250')
    philhealth_monthly_min  = models.DecimalField(max_digits=10, decimal_places=2, default='10000.00')
    philhealth_monthly_max  = models.DecimalField(max_digits=10, decimal_places=2, default='100000.00')

    pagibig_monthly_max     = models.DecimalField(max_digits=10, decimal_places=2, default='10000.00')
    pagibig_low_rate        = models.DecimalField(max_digits=6,  decimal_places=4, default='0.0100')
    pagibig_standard_rate   = models.DecimalField(max_digits=6,  decimal_places=4, default='0.0200')
    pagibig_low_rate_limit  = models.DecimalField(max_digits=10, decimal_places=2, default='1500.00')

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='deduction_config_updates',
    )

    class Meta:
        verbose_name = 'Deduction Configuration'

    @classmethod
    def get(cls):
        """Always returns a config — creates the default one if none exists yet."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return f"Deduction Config (updated {self.updated_at.date() if self.updated_at else 'never'})"