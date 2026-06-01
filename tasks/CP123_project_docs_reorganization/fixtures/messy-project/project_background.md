# Invoice Processing System - Project Background

## Business Context

The company partners with multiple cloud vendors (AWS, GCP, Azure) and needs to process
monthly billing invoices from each vendor, calculate commissions for sales partners,
and produce consolidated profit reports.

## Core Requirements

1. Extract invoice data from vendor portals (browser automation + API)
2. Validate extracted data against vendor-provided Excel/CSV templates
3. Calculate partner commissions based on tiered rules
4. Generate monthly profit/loss reports
5. Integrate with Lark/Feishu approval workflow for commission sign-off

## Data Sources

- AWS monthly billing CSV exports
- GCP BigQuery billing export (JSON)
- Azure Cost Management API (REST)
- Partner portal Excel uploads
- Internal CRM system

## Related Documents

- [Vendor Invoice Field Mapping](./vendor_invoice_field_mapping.md)
- [Cloud Vendor Billing](./cloud_vendor_billing.md)
- [Partner Commission](./partner_commission.md)
- [Profit Report](./profit_report.md)
- [Approval UI Elements](./approval_ui_elements.md)

## History

This project started as a manual spreadsheet process. v1 was a set of scripts.
v2 (current) is a full web application with scheduled jobs.
