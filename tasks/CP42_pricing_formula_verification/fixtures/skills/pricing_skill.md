# Product Pricing Strategy Standardized Delivery Skill V1.0

## Applicable Scope
All multi-tier recharge strategies, membership pricing, value-added service pricing, and any pricing tasks involving formula calculations, multi-rule constraints, and multi-scenario outputs.

## Core Execution Flow

### Phase 1: Requirement Confirmation
1. Receive and parse all pricing rules, formulas, constraints, and output fields
2. Structure rules into a Checklist
3. Confirm with requester before proceeding

### Phase 2: Formula Parsing and Parameter Alignment
1. Identify all variables in the pricing formula
2. Confirm unit conversions (e.g., percentage vs decimal)
3. Validate formula structure for mathematical correctness

### Phase 3: Calculation Execution
1. Calculate each tier independently using the confirmed formula
2. Record intermediate calculation steps for auditability
3. Apply constraints (e.g., monotonicity, range limits)

### Phase 4: Cross-Validation
1. Verify results against all stated rules
2. Check inter-tier monotonicity (higher tier => more benefits)
3. Validate cost ratios within acceptable ranges
4. Confirm gross margin targets are met per tier

### Phase 5: Delivery
1. Produce structured output document
2. Include rule compliance checklist
3. Include all calculation steps for reproducibility

## Key Formulas

### Recharge-to-Bonus Ratio
```
ratio = (1/(margin+1) - 1/(margin+1) * (bonus_cost/tier_price*(margin+1)) - 1*sharing_ratio) * (1+premium_ratio) - 1
```

Variables:
- margin (Gross Margin Target): decimal, e.g., 0.40 for 40%
- bonus_cost (Bonus Feature Cost): monetary value in CNY
- tier_price (Tier Price): monetary value in CNY
- sharing_ratio (Bonus Sharing Ratio): decimal
- premium_ratio (Model Premium Ratio): decimal

### Critical Rules
1. All percentage values MUST be converted to decimals before calculation
2. Higher tiers MUST receive more bonus than lower tiers (monotonicity)
3. Bonus feature cost ratio must be between 5%-10% of total cost
4. Gross margin must stay within 20%-40% range across all tiers
