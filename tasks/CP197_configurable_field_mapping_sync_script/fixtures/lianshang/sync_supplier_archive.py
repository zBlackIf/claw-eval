#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Supplier archive sync script.

Data flow: Upstream API (Huijin) -> Downstream system (Jiandaoyun SRM)

Sync strategy:
  - Unique key: supplier code
  - Full mode: create all missing records
  - Incremental mode: create missing, update existing if changed

Current issues (TODO):
  - Field mapping is hardcoded in the sync logic
  - Sub-table field name "banks" is hardcoded, but downstream uses "gyszhxx_items"
  - No way to change field mapping without editing code
  - Change detection doesn't handle sub-table comparison
"""
import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== HARDCODED MAPPING (needs to be configurable) ====================

def convert_supplier_to_downstream(supplier_data):
    """Convert upstream supplier data to downstream format.

    Problem: mapping is hardcoded. If upstream changes field names
    (e.g. 'banks' becomes 'items'), we must edit this function.
    """
    result = {}

    # Main table fields - hardcoded
    result["supplier_code"] = {"value": supplier_data.get("code", "")}
    result["supplier_full_name"] = {"value": supplier_data.get("fullName", "")}
    result["supplier_short_name"] = {"value": supplier_data.get("shortName", "")}
    result["supplier_type"] = {"value": supplier_data.get("type", "")}
    result["receipt_account"] = {"value": supplier_data.get("receiptAccount", "")}
    result["receipt_bank"] = {"value": supplier_data.get("receiptBank", "")}
    result["receipt_company"] = {"value": supplier_data.get("receiptCompany", "")}

    # Sub-table fields - hardcoded "banks" name
    banks = supplier_data.get("banks", [])
    if banks:
        subform_rows = []
        for bank in banks:
            row = {
                "bank_account": {"value": bank.get("account", "")},
                "bank_account_name": {"value": bank.get("accountName", "")},
                "bank_name": {"value": bank.get("bankName", "")},
                "bank_property": {"value": bank.get("bankAccountProperty", "")},
            }
            subform_rows.append(row)
        # Problem: downstream field name is hardcoded as "banks"
        # but downstream system actually uses "gyszhxx_items"
        result["banks"] = {"value": subform_rows}

    return result


def detect_changes(existing_record, new_data):
    """Detect if any field has changed.

    Problem: only compares main table fields, ignores sub-table changes.
    """
    changed = False
    for field_name, value_obj in new_data.items():
        if field_name == "banks":
            # TODO: sub-table comparison not implemented
            continue
        new_value = value_obj.get("value", "")
        old_value = existing_record.get(field_name, {}).get("value", "")
        if str(new_value) != str(old_value):
            changed = True
            break
    return changed


def sync_suppliers(upstream_data, downstream_data, full=False):
    """Main sync logic.

    Args:
        upstream_data: dict of {code: supplier_data} from upstream API
        downstream_data: dict of {code: {"id": record_id, "data": fields}} from downstream
        full: if True, sync all; if False, only today's changes

    Returns:
        dict with keys: created, updated, skipped, errors
    """
    results = {"created": [], "updated": [], "skipped": [], "errors": []}

    upstream_codes = set(upstream_data.keys())
    downstream_codes = set(downstream_data.keys())

    to_create = upstream_codes - downstream_codes
    to_check = upstream_codes & downstream_codes

    # Create new records
    for code in to_create:
        converted = convert_supplier_to_downstream(upstream_data[code])
        results["created"].append({"code": code, "data": converted})

    # Check existing for updates
    for code in to_check:
        converted = convert_supplier_to_downstream(upstream_data[code])
        existing = downstream_data[code]["data"]
        if detect_changes(existing, converted):
            results["updated"].append({
                "code": code,
                "record_id": downstream_data[code]["id"],
                "data": converted,
            })
        else:
            results["skipped"].append(code)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supplier archive sync")
    parser.add_argument("--full", action="store_true", help="Full sync mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run, no actual writes")
    args = parser.parse_args()

    print(f"Sync mode: {'full' if args.full else 'incremental'}")
    print("Note: This script requires upstream/downstream service connections.")
    print("Run with test data for development.")
