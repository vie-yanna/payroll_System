from django.db import migrations


def backfill_payroll_records(apps, schema_editor):
    PayrollRecord = apps.get_model('payroll', 'PayrollRecord')
    from payroll.payroll_calculator import calculate_cutoff_pay

    for record in PayrollRecord.objects.all():
        total_cutoff_days = record.total_cutoff_days or record.days_worked
        values = calculate_cutoff_pay(
            total_cutoff_days=total_cutoff_days,
            absent_days=record.absent_days,
            rate_per_day=record.rate_per_day,
        )
        record.total_cutoff_days = total_cutoff_days
        for field, value in values.items():
            setattr(record, field, value)
        record.save(update_fields=[
            'total_cutoff_days',
            'days_worked',
            'gross_pay',
            'absent_deduction',
            'salary',
            'sss_deduction',
            'philhealth_deduction',
            'pagibig_deduction',
            'withholding_tax',
            'taxable_pay',
            'total_deductions',
            'net_pay',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0005_alter_payrollrecord_options_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_payroll_records, migrations.RunPython.noop),
    ]
