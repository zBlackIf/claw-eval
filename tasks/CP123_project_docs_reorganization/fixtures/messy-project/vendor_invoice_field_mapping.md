# Vendor Invoice Field Mapping

## AWS Monthly Billing

| Source Field | Target Column | Type | Notes |
|---|---|---|---|
| lineItem/UsageStartDate | billing_period_start | date | UTC |
| lineItem/UsageEndDate | billing_period_end | date | UTC |
| lineItem/ProductCode | service_name | string | |
| lineItem/UnblendedCost | amount | decimal | USD |
| lineItem/CurrencyCode | currency | string | Always USD |

## GCP Billing Export

| Source Field | Target Column | Type | Notes |
|---|---|---|---|
| billing_account_id | vendor_account | string | |
| service.description | service_name | string | |
| cost | amount | decimal | |
| currency | currency | string | |
| usage_start_time | billing_period_start | timestamp | |

## Azure Cost Management

| Source Field | Target Column | Type | Notes |
|---|---|---|---|
| SubscriptionId | vendor_account | string | GUID |
| ServiceName | service_name | string | |
| CostInBillingCurrency | amount | decimal | |
| BillingCurrency | currency | string | |
| Date | billing_period_start | date | |
