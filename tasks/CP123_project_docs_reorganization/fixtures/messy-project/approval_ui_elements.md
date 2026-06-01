# Approval UI Elements

## Commission Approval Form Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| partner_name | text | yes | Auto-filled |
| period | date_range | yes | Month being approved |
| total_revenue | currency | yes | Calculated |
| commission_amount | currency | yes | Calculated |
| commission_rate | percentage | yes | Based on tier |
| approver_notes | textarea | no | Free text |
| attachment | file[] | no | Supporting docs |

## Approval Status Transitions

```
draft -> pending_review -> approved -> paid
                       -> rejected -> draft (revision)
```

## UI Mockup Notes

- Green highlight for auto-approved items
- Yellow for pending human approval
- Red border for rejected items
