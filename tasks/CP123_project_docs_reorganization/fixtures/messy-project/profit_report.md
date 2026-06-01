# Profit Report Specification

## Report Structure

Monthly profit/loss report contains:

1. **Revenue Summary** - Total billable revenue by vendor
2. **Cost Breakdown** - Infrastructure + partner commissions + overhead
3. **Margin Analysis** - Per-vendor and per-partner margins
4. **Trend Comparison** - MoM and YoY comparison

## Output Format

- Excel workbook with multiple sheets
- PDF summary for leadership
- JSON API endpoint for dashboard

## Data Dependencies

- Billing records (from vendor extraction)
- Commission calculations (from partner_commission rules)
- Cost allocations (from internal accounting)
