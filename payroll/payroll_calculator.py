from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal('0.01')

ANNUAL_TAX_PERIODS = Decimal('24')
SSS_EMPLOYEE_RATE = Decimal('0.05')
SSS_MONTHLY_MIN = Decimal('5000.00')
SSS_MONTHLY_MAX = Decimal('35000.00')
PHILHEALTH_EMPLOYEE_RATE = Decimal('0.025')
PHILHEALTH_MONTHLY_MIN = Decimal('10000.00')
PHILHEALTH_MONTHLY_MAX = Decimal('100000.00')
PAGIBIG_MONTHLY_MAX = Decimal('10000.00')
PAGIBIG_LOW_RATE = Decimal('0.01')
PAGIBIG_STANDARD_RATE = Decimal('0.02')
PAGIBIG_LOW_RATE_LIMIT = Decimal('1500.00')


def money(value):
    return Decimal(value or 0).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def clamp(value, minimum, maximum):
    return min(max(value, minimum), maximum)


def annual_income_tax(annual_taxable_income):
    income = money(annual_taxable_income)

    if income <= Decimal('250000.00'):
        return Decimal('0.00')
    if income <= Decimal('400000.00'):
        return money((income - Decimal('250000.00')) * Decimal('0.15'))
    if income <= Decimal('800000.00'):
        return money(Decimal('22500.00') + ((income - Decimal('400000.00')) * Decimal('0.20')))
    if income <= Decimal('2000000.00'):
        return money(Decimal('102500.00') + ((income - Decimal('800000.00')) * Decimal('0.25')))
    if income <= Decimal('8000000.00'):
        return money(Decimal('402500.00') + ((income - Decimal('2000000.00')) * Decimal('0.30')))
    return money(Decimal('2202500.00') + ((income - Decimal('8000000.00')) * Decimal('0.35')))


def per_cutoff_contributions(cutoff_pay, periods_per_year=ANNUAL_TAX_PERIODS):
    periods = Decimal(periods_per_year or ANNUAL_TAX_PERIODS)
    cutoffs_per_month = periods / Decimal('12')
    monthly_equivalent = money(Decimal(cutoff_pay or 0) * cutoffs_per_month)

    if monthly_equivalent <= 0:
        return {
            'sss_deduction': Decimal('0.00'),
            'philhealth_deduction': Decimal('0.00'),
            'pagibig_deduction': Decimal('0.00'),
        }

    sss_base = clamp(monthly_equivalent, SSS_MONTHLY_MIN, SSS_MONTHLY_MAX)
    philhealth_base = clamp(monthly_equivalent, PHILHEALTH_MONTHLY_MIN, PHILHEALTH_MONTHLY_MAX)
    pagibig_base = min(monthly_equivalent, PAGIBIG_MONTHLY_MAX)
    pagibig_rate = PAGIBIG_LOW_RATE if monthly_equivalent <= PAGIBIG_LOW_RATE_LIMIT else PAGIBIG_STANDARD_RATE

    return {
        'sss_deduction': money((sss_base * SSS_EMPLOYEE_RATE) / cutoffs_per_month),
        'philhealth_deduction': money((philhealth_base * PHILHEALTH_EMPLOYEE_RATE) / cutoffs_per_month),
        'pagibig_deduction': money((pagibig_base * pagibig_rate) / cutoffs_per_month),
    }


def calculate_cutoff_pay(total_cutoff_days, absent_days, rate_per_day, periods_per_year=ANNUAL_TAX_PERIODS):
    periods = Decimal(periods_per_year or ANNUAL_TAX_PERIODS)
    cutoff_days = Decimal(total_cutoff_days or 0)
    absences = Decimal(absent_days or 0)
    rate = money(rate_per_day)

    paid_days = max(cutoff_days - absences, Decimal('0.00'))
    gross_pay = money(cutoff_days * rate)
    absent_deduction = money(absences * rate)
    cutoff_pay = money(paid_days * rate)
    contributions = per_cutoff_contributions(cutoff_pay, periods)
    taxable_pay = money(cutoff_pay - sum(contributions.values(), Decimal('0.00')))
    withholding_tax = money(annual_income_tax(taxable_pay * periods) / periods)
    statutory_deductions = money(sum(contributions.values(), Decimal('0.00')) + withholding_tax)
    total_deductions = money(absent_deduction + statutory_deductions)
    net_pay = money(gross_pay - total_deductions)

    return {
        'days_worked': paid_days,
        'gross_pay': gross_pay,
        'absent_deduction': absent_deduction,
        'salary': cutoff_pay,
        'taxable_pay': taxable_pay,
        'withholding_tax': withholding_tax,
        'total_deductions': total_deductions,
        'net_pay': net_pay,
        **contributions,
    }
