# accounts/migrations/0003_backfill_employee_numbers.py
"""
Data migration: assign employee numbers to existing users.
Uses the same logic as User.generate_employee_number().
"""
from django.db import migrations


def backfill_employee_numbers(apps, schema_editor):
    """
    Loop over all users without an employee_number and assign
    the next available sequential number.
    """
    User = apps.get_model('accounts', 'User')

    # Collect existing employee numbers matching EMP-XXXXX
    existing = User.objects.filter(
        employee_number__isnull=False,
        employee_number__startswith='EMP-'
    ).values_list('employee_number', flat=True)

    max_num = 0
    for num in existing:
        try:
            val = int(num.split('-')[1])
            if val > max_num:
                max_num = val
        except (IndexError, ValueError):
            # Ignore malformed numbers
            continue

    # Get all users without an employee number
    users_without_number = User.objects.filter(employee_number__isnull=True)

    # Assign sequentially
    for user in users_without_number:
        max_num += 1
        user.employee_number = f"EMP-{max_num:05d}"
        user.save(update_fields=['employee_number'])


def reverse_backfill(apps, schema_editor):
    """
    Optional reverse: clear employee numbers that were auto‑generated
    (only those that start with EMP-).
    """
    User = apps.get_model('accounts', 'User')
    User.objects.filter(employee_number__startswith='EMP-').update(employee_number=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_loginhistory_useractivity'),  # adjust if your previous migration has a different name
    ]

    operations = [
        migrations.RunPython(backfill_employee_numbers, reverse_backfill),
    ]