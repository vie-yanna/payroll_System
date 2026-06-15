# Payroll System Backend

This project is a Django backend for a payroll system.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   .\\venv\\Scripts\\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Create a superuser for the admin interface (optional):
   ```bash
   python manage.py createsuperuser
   ```
5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

Base API path: `/api/payroll/`

- `employees/`
- `periods/`
- `salary-components/`
- `payroll-runs/`

### Run payroll

POST to `/api/payroll/payroll-runs/` with JSON:

```json
{
  "period_id": 1
}
```

This generates `PayrollItem` records for all active employees and calculates gross/net totals.
