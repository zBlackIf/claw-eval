# Incidence Rate Validation Plan

## Context

We are validating CardioOmicScore paper's 9 cardiovascular disease endpoints
using our preprocessed data. Initial results show systematically low incidence
rates (approximately half of paper-reported values).

## Known Issues

1. **ICD code coverage**: Our code lists may be incomplete compared to the
   paper's official S1_OutcomesGenerator.py. Need to cross-check every
   disease's three-digit ICD-10 codes.

2. **Follow-up window**: We use 15-year follow-up labels. The paper follows
   up to November 2023 (up to 17 years). This 2-year gap contributes to
   lower rates.

3. **CVDeath endpoint**: We lack a separate cardiovascular death label.
   Need to locate or construct this from cause-of-death data.

## Paper's Official ICD Code Lists

From S1_OutcomesGenerator.py:

| Disease | ICD-10 Three-digit Codes |
|---------|--------------------------|
| CAD     | I20, I21, I22, I23, I24, I25 |
| Stroke  | I60, I61, I62, I63 |
| HF      | I11, I13, I25, I42, I50 |
| AF      | I48 |
| VA      | I46, I47, I49 |
| PAD     | I70, I73 |
| AAA     | I71 |
| VTE     | I26, I80, I81, I82 |

## Task

1. Update validate_incidence_rate.py to fix any missing ICD codes
2. Re-run the validation
3. Generate incidence_rate_comparison.csv with results
4. Write analysis_notes.md summarizing findings and remaining discrepancies
