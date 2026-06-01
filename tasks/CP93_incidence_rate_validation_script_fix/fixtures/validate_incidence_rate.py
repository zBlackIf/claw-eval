#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CardiOmicScore Incidence Rate Validation
Validate 9 cardiovascular disease endpoints against paper-reported rates
using preprocessed parquet-format disease labels.

Modified to use CSV snapshots for portability.
"""

import csv
import os
import sys

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Paper-reported results (from Supplementary Figure 1)
# ICD code lists from S1_OutcomesGenerator.py
PAPER_RESULTS = [
    {"short_name": "CAD", "disease_name": "Coronary artery disease",
     "paper_events": 1794, "paper_rate": 16.6,
     "codes": ["I20", "I21", "I22", "I23", "I24", "I25"]},
    {"short_name": "stroke", "disease_name": "Stroke",
     "paper_events": 583, "paper_rate": 5.4,
     "codes": ["I60", "I61", "I62", "I63"]},
    {"short_name": "HF", "disease_name": "Heart failure",
     "paper_events": 799, "paper_rate": 7.4,
     "codes": ["I11", "I13", "I25", "I42", "I50"]},
    {"short_name": "AF", "disease_name": "Atrial fibrillation",
     "paper_events": 1527, "paper_rate": 14.1,
     "codes": ["I48"]},
    {"short_name": "VA", "disease_name": "Ventricular arrhythmias",
     "paper_events": 232, "paper_rate": 2.1,
     "codes": ["I46", "I47", "I49"]},
    {"short_name": "PAD", "disease_name": "Peripheral artery disease",
     "paper_events": 321, "paper_rate": 3.0,
     "codes": ["I70"]},
    {"short_name": "AAA", "disease_name": "Abdominal aortic aneurysm",
     "paper_events": 123, "paper_rate": 1.1,
     "codes": ["I71"]},
    {"short_name": "VTE", "disease_name": "Venous thromboembolism",
     "paper_events": 682, "paper_rate": 6.3,
     "codes": ["I26", "I80", "I81", "I82"]},
    {"short_name": "CVDeath", "disease_name": "Cardiovascular death",
     "paper_events": 563, "paper_rate": 5.2,
     "is_cvd_death": True},
]


def load_csv_data(filepath):
    """Load CSV file, return list of dicts."""
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(row)
    return rows


def compute_incidence_rates(labels_file, baseline_file, cohort_file, output_dir):
    """
    Compute incidence rates for each disease endpoint.

    Args:
        labels_file: CSV with disease labels (columns: eid, XXX_15year)
        baseline_file: CSV with baseline disease status (columns: eid, XXX)
        cohort_file: CSV with cohort eids (columns: eid)
        output_dir: directory for output files
    """
    print("=" * 70)
    print("Step 1: Load data")
    print("=" * 70)

    cohort_rows = load_csv_data(cohort_file)
    cohort_eids = set(row["eid"] for row in cohort_rows)
    print(f"Multiomics cohort: {len(cohort_eids)} participants")

    labels_rows = load_csv_data(labels_file)
    baseline_rows = load_csv_data(baseline_file)
    print(f"Disease labels: {len(labels_rows)} rows")
    print(f"Baseline status: {len(baseline_rows)} rows")

    # Filter to cohort
    labels_rows = [r for r in labels_rows if r["eid"] in cohort_eids]
    baseline_rows = [r for r in baseline_rows if r["eid"] in cohort_eids]
    print(f"After filter - labels: {len(labels_rows)}, baseline: {len(baseline_rows)}")

    # Index baseline by eid
    baseline_by_eid = {r["eid"]: r for r in baseline_rows}

    # Get available columns
    label_cols = set(labels_rows[0].keys()) if labels_rows else set()
    baseline_cols = set(baseline_rows[0].keys()) if baseline_rows else set()

    print()
    print("=" * 70)
    print("Step 2: Compute incidence rates")
    print("=" * 70)

    results = []
    for item in PAPER_RESULTS:
        if item.get("is_cvd_death"):
            print(f"  CVDeath: requires separate death cause data, skipping")
            continue

        codes = item["codes"]
        short_name = item["short_name"]

        # Find matching columns
        matching_label_cols = [f"{c}_15year" for c in codes if f"{c}_15year" in label_cols]
        matching_baseline_cols = [c for c in codes if c in baseline_cols]

        if not matching_label_cols:
            print(f"  {short_name}: no matching label columns found, skipping")
            continue

        # Count eligible (no baseline disease) and incident cases
        eligible_count = 0
        incident_count = 0

        for row in labels_rows:
            eid = row["eid"]
            baseline = baseline_by_eid.get(eid, {})

            # Check baseline exclusion
            has_baseline = any(
                baseline.get(col, "0") == "1"
                for col in matching_baseline_cols
            )
            if has_baseline:
                continue

            eligible_count += 1

            # Check incident disease
            has_incident = any(
                row.get(col, "0") == "1"
                for col in matching_label_cols
            )
            if has_incident:
                incident_count += 1

        our_rate = (incident_count / eligible_count * 100) if eligible_count > 0 else 0
        diff = our_rate - item["paper_rate"]

        print(f"  {short_name:>8s}: eligible={eligible_count}  events={incident_count:>5d}  "
              f"rate={our_rate:>5.2f}%  paper_rate={item['paper_rate']}%  diff={diff:+.2f}%")

        results.append({
            "disease": short_name,
            "eligible": eligible_count,
            "our_events": incident_count,
            "our_rate_pct": round(our_rate, 2),
            "paper_events": item["paper_events"],
            "paper_rate_pct": item["paper_rate"],
            "diff_pct": round(diff, 2),
            "relative_diff_pct": round((diff / item["paper_rate"]) * 100, 1) if item["paper_rate"] > 0 else 0,
        })

    # Save results
    print()
    print("=" * 70)
    print("Step 3: Save results")
    print("=" * 70)

    csv_path = os.path.join(output_dir, "incidence_rate_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "disease", "eligible", "our_events", "our_rate_pct",
            "paper_events", "paper_rate_pct", "diff_pct", "relative_diff_pct"
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved to: {csv_path}")

    return results


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    labels_file = os.path.join(script_dir, "disease_labels_15year.csv")
    baseline_file = os.path.join(script_dir, "baseline_disease_status.csv")
    cohort_file = os.path.join(script_dir, "cohort_eids.csv")

    compute_incidence_rates(labels_file, baseline_file, cohort_file, script_dir)
    print("\nDone!")
