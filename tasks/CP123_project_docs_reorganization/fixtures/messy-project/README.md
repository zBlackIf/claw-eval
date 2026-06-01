# Invoice Processing System

A system to automate invoice extraction, validation, and reconciliation for multiple vendors.

## Quick Start

```bash
pip install -r requirements.txt
python -m app.main
```

## Documentation

- Business rules (single source of truth): `project_background.md`
- Technical implementation spec: `docs/draft2_technical_detailed.md`
- Data mapping: `vendor_invoice_field_mapping.md`

## Documentation Map

- [Vendor Invoice Field Mapping](./vendor_invoice_field_mapping.md)
- [Cloud Vendor Billing](./cloud_vendor_billing.md)
- [Partner Commission](./partner_commission.md)
- [Profit Report](./profit_report.md)
- [Project Background](./project_background.md)

## Tech Stack

- Python 3.11
- FastAPI
- PostgreSQL
- Celery + Redis
