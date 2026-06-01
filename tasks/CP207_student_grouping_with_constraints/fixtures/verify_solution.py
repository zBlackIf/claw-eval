"""Hidden verifier for CP207 — Student Grouping with Constraints.

Tiered hidden checks:
  - EASY tier: lenient thresholds that any reasonable agent should pass
    (data_integrity_easy, field_completeness_easy, phone_format_valid)
  - HARD tier: strict thresholds only strong agents pass
    (data_integrity_strict, phone_accuracy_exact, age_data_accuracy,
     industry_counts_exact, gender_percentage)

Hidden checks (easy + hard) together account for >= 30% of total weight.
"""
from __future__ import annotations

import json
import csv
import re
from pathlib import Path
from typing import Any


def _load_csv(path: Path) -> list[dict]:
    """Load student CSV into list of dicts."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception:
        pass
    return rows


def _load_json(path: Path) -> Any:
    """Load JSON file safely."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _check_profile(profile: dict, students: list[dict]) -> dict:
    """Check profile analysis correctness."""
    scores = {}

    # Gender distribution check
    actual_female = sum(1 for s in students if s.get("性别", "").strip() == "女")
    actual_male = sum(1 for s in students if s.get("性别", "").strip() == "男")
    total = len(students)

    gender_score = 0.0
    gender_data = profile.get("gender") or profile.get("性别分布") or profile.get("gender_distribution") or {}
    if isinstance(gender_data, dict):
        found_female = None
        found_male = None
        for k, v in gender_data.items():
            kl = k.lower()
            # Extract count from either direct int or nested dict
            count_val = None
            if isinstance(v, (int, float)):
                count_val = v
            elif isinstance(v, dict):
                count_val = v.get("人数") or v.get("count") or v.get("num")
                if not isinstance(count_val, (int, float)):
                    count_val = None
            if "女" in kl or "female" in kl:
                found_female = count_val
            if "男" in kl or "male" in kl:
                found_male = count_val
        if found_female is not None and abs(found_female - actual_female) <= 1:
            gender_score += 0.5
        if found_male is not None and abs(found_male - actual_male) <= 1:
            gender_score += 0.5
    scores["gender_distribution"] = gender_score

    # HARD hidden: Gender percentage accuracy — requires exact calculation
    female_pct_actual = round(actual_female / total * 100, 1)
    male_pct_actual = round(actual_male / total * 100, 1)
    pct_score = 0.0

    def _extract_pct(val: Any) -> float | None:
        """Extract percentage value from various formats."""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            cleaned = val.replace("%", "").replace("％", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    if isinstance(gender_data, dict):
        for k, v in gender_data.items():
            kl = k.lower()
            pct_val = None
            if isinstance(v, dict):
                for pct_key in ["percentage", "占比", "pct", "ratio", "percent"]:
                    raw = v.get(pct_key)
                    if raw is not None:
                        pct_val = _extract_pct(raw)
                        if pct_val is not None:
                            break
            elif isinstance(v, str) and ("%" in v or "％" in v):
                pct_val = _extract_pct(v)
            if pct_val is not None:
                if ("女" in kl or "female" in kl) and abs(pct_val - female_pct_actual) < 1.0:
                    pct_score += 0.5
                elif ("男" in kl or "male" in kl) and abs(pct_val - male_pct_actual) < 1.0:
                    pct_score += 0.5
    for pct_key_name in ["gender_percentage", "性别占比", "percentage"]:
        pct_data = profile.get(pct_key_name)
        if isinstance(pct_data, dict):
            for k, v in pct_data.items():
                pv = _extract_pct(v)
                if pv is not None:
                    kl = k.lower()
                    if ("女" in kl or "female" in kl) and abs(pv - female_pct_actual) < 1.0:
                        pct_score += 0.5
                    elif ("男" in kl or "male" in kl) and abs(pv - male_pct_actual) < 1.0:
                        pct_score += 0.5
    scores["gender_percentage"] = min(pct_score, 1.0)

    # Age distribution check
    age_bins = {"16-30": 0, "31-40": 0, "41-50": 0, "51-60": 0}
    for s in students:
        try:
            age = int(s.get("年龄", 0))
        except (ValueError, TypeError):
            continue
        if 16 <= age <= 30:
            age_bins["16-30"] += 1
        elif 31 <= age <= 40:
            age_bins["31-40"] += 1
        elif 41 <= age <= 50:
            age_bins["41-50"] += 1
        elif 51 <= age <= 60:
            age_bins["51-60"] += 1

    age_data = profile.get("age") or profile.get("年龄分布") or profile.get("age_distribution") or {}
    age_score = 0.0
    if isinstance(age_data, dict):
        matched = 0
        for bin_key, actual_count in age_bins.items():
            for k, v in age_data.items():
                if bin_key in k or (bin_key.replace("-", "~") in k) or (bin_key.replace("-", "—") in k):
                    if isinstance(v, (int, float)) and abs(v - actual_count) <= 1:
                        matched += 1
                    elif isinstance(v, dict):
                        cnt = v.get("count") or v.get("人数") or v.get("num")
                        if isinstance(cnt, (int, float)) and abs(cnt - actual_count) <= 1:
                            matched += 1
                    break
        age_score = matched / 4.0
    scores["age_distribution"] = age_score

    # Average age check
    ages = []
    for s in students:
        try:
            ages.append(int(s.get("年龄", 0)))
        except (ValueError, TypeError):
            pass
    actual_avg = sum(ages) / len(ages) if ages else 0
    avg_reported = profile.get("average_age") or profile.get("平均年龄") or profile.get("avg_age")
    if isinstance(avg_reported, (int, float)) and abs(avg_reported - actual_avg) < 1.0:
        scores["average_age"] = 1.0
    elif isinstance(avg_reported, (int, float)) and abs(avg_reported - actual_avg) < 2.0:
        scores["average_age"] = 0.5
    else:
        scores["average_age"] = 0.0

    # Location distribution check
    yiwu_count = sum(1 for s in students if "义乌" in s.get("户籍所在地", "").replace(" ", ""))
    non_yiwu = total - yiwu_count
    loc_data = profile.get("location") or profile.get("户籍分布") or profile.get("location_distribution") or {}
    loc_score = 0.0
    if isinstance(loc_data, dict):
        for k, v in loc_data.items():
            val = v
            if isinstance(v, dict):
                val = v.get("count") or v.get("人数") or v.get("num") or 0
            if isinstance(val, (int, float)):
                if ("义乌" in k or "yiwu" in k.lower()) and abs(val - yiwu_count) <= 1:
                    loc_score += 0.5
                elif ("非" in k or "other" in k.lower() or "non" in k.lower() or "金华" in k) and abs(val - non_yiwu) <= 1:
                    loc_score += 0.5
    scores["location_distribution"] = loc_score

    # Industry distribution check (top 5)
    industry_counts: dict[str, int] = {}
    for s in students:
        ind = s.get("从事行业", "").strip()
        if ind:
            industry_counts[ind] = industry_counts.get(ind, 0) + 1
    top5_actual = sorted(industry_counts.items(), key=lambda x: -x[1])[:5]
    ind_data = profile.get("industry") or profile.get("行业分布") or profile.get("industry_distribution") or {}
    ind_score = 0.0
    if isinstance(ind_data, (dict, list)):
        actual_top_names = {name for name, _ in top5_actual}
        if isinstance(ind_data, dict):
            reported_names = set(ind_data.keys())
        else:
            reported_names = set()
            for item in ind_data:
                if isinstance(item, dict):
                    name_val = item.get("行业") or item.get("industry") or item.get("name") or ""
                    if name_val:
                        reported_names.add(str(name_val))
                    else:
                        for k in item:
                            reported_names.add(str(item.get(k, "")))
                elif isinstance(item, str):
                    reported_names.add(item)
        overlap = len(actual_top_names & reported_names)
        ind_score = min(overlap / 3.0, 1.0)

    # HARD hidden: exact industry counts
    ind_count_score = 0.0
    if isinstance(ind_data, dict):
        correct_counts = 0
        for name, count in top5_actual:
            reported_val = ind_data.get(name)
            if isinstance(reported_val, (int, float)) and abs(reported_val - count) <= 0:
                correct_counts += 1
            elif isinstance(reported_val, dict):
                cnt = reported_val.get("count") or reported_val.get("人数") or reported_val.get("num")
                if isinstance(cnt, (int, float)) and abs(cnt - count) <= 0:
                    correct_counts += 1
        ind_count_score = correct_counts / 5.0
    elif isinstance(ind_data, list):
        correct_counts = 0
        for item in ind_data:
            if isinstance(item, dict):
                name_val = item.get("行业") or item.get("industry") or item.get("name") or ""
                cnt_val = item.get("count") or item.get("人数") or item.get("num") or item.get("数量")
                for actual_name, actual_count in top5_actual:
                    if str(name_val) == actual_name and isinstance(cnt_val, (int, float)) and abs(cnt_val - actual_count) <= 0:
                        correct_counts += 1
                        break
        ind_count_score = correct_counts / 5.0

    scores["industry_distribution"] = ind_score
    scores["industry_counts_exact"] = ind_count_score

    return scores


def _check_grouping(grouping: Any, students: list[dict]) -> dict:
    """Check grouping result against constraints."""
    scores = {}

    zero_scores = {
        "group_structure": 0.0, "specified_together": 0.0, "group_sizes": 0.0,
        "youth_distribution": 0.0, "age_balance": 0.0,
        # Easy hidden
        "data_integrity_easy": 0.0, "field_completeness_easy": 0.0, "phone_format_valid": 0.0,
        # Hard hidden
        "data_integrity_strict": 0.0, "phone_accuracy_exact": 0.0, "age_data_accuracy": 0.0,
    }

    if not isinstance(grouping, (dict, list)):
        return zero_scores

    # Normalize grouping to list of groups
    groups: list[list[dict]] = []
    if isinstance(grouping, dict):
        if "groups" in grouping:
            groups_raw = grouping["groups"]
        else:
            groups_raw = list(grouping.values())
        for g in groups_raw:
            if isinstance(g, list):
                groups.append(g)
            elif isinstance(g, dict) and "members" in g:
                groups.append(g["members"])
            elif isinstance(g, dict) and "学员" in g:
                groups.append(g["学员"])
    elif isinstance(grouping, list):
        for g in grouping:
            if isinstance(g, list):
                groups.append(g)
            elif isinstance(g, dict) and "members" in g:
                groups.append(g["members"])
            elif isinstance(g, dict) and "学员" in g:
                groups.append(g["学员"])

    if len(groups) == 0:
        return zero_scores

    # Basic structure: should have 4 groups
    scores["group_structure"] = 1.0 if len(groups) == 4 else (0.5 if len(groups) in [3, 5] else 0.0)

    # Extract names from each group
    def extract_name(member: Any) -> str:
        if isinstance(member, dict):
            return str(member.get("姓名", member.get("name", ""))).strip()
        elif isinstance(member, str):
            return member.strip()
        return ""

    def extract_phone(member: Any) -> str:
        if isinstance(member, dict):
            return str(member.get("手机号码", member.get("phone", member.get("手机", "")))).strip()
        return ""

    def extract_age(member: Any) -> int | None:
        if isinstance(member, dict):
            raw = member.get("年龄") or member.get("age")
            if raw is not None:
                try:
                    return int(raw)
                except (ValueError, TypeError):
                    pass
        return None

    group_names: list[list[str]] = []
    group_members: list[list[Any]] = []
    for g in groups:
        names = [extract_name(m) for m in g]
        group_names.append([n for n in names if n])
        group_members.append(g)

    # Build student lookup
    student_by_name = {s["姓名"].strip(): s for s in students if s.get("姓名")}
    all_student_names = set(student_by_name.keys())

    # Collect all assigned names
    all_assigned_names = []
    for names in group_names:
        all_assigned_names.extend(names)
    assigned_set = set(all_assigned_names)

    missing = all_student_names - assigned_set
    extra = assigned_set - all_student_names
    duplicates = len(all_assigned_names) - len(assigned_set)

    # ===== EASY HIDDEN: Data integrity (lenient) =====
    # At least 40 of 45 students present, no more than 3 duplicates
    if len(assigned_set & all_student_names) >= 40 and duplicates <= 3:
        scores["data_integrity_easy"] = 1.0
    elif len(assigned_set & all_student_names) >= 35:
        scores["data_integrity_easy"] = 0.6
    else:
        scores["data_integrity_easy"] = 0.0

    # ===== HARD HIDDEN: Data integrity (strict) =====
    # All 45 students exactly once — zero missing, zero extra, zero duplicates
    if len(missing) == 0 and len(extra) == 0 and duplicates == 0:
        scores["data_integrity_strict"] = 1.0
    elif len(missing) <= 1 and duplicates == 0 and len(extra) == 0:
        scores["data_integrity_strict"] = 0.7
    elif len(missing) <= 2 and duplicates <= 1:
        scores["data_integrity_strict"] = 0.3
    else:
        scores["data_integrity_strict"] = 0.0

    # ===== EASY HIDDEN: Field completeness (lenient) =====
    # At least 80% of members have all 4 required fields
    required_fields_variants = {
        "name": ["姓名", "name", "学员"],
        "age": ["年龄", "age"],
        "gender": ["性别", "gender", "sex"],
        "phone": ["手机号码", "phone", "手机", "电话", "tel"],
    }
    total_members = 0
    fields_complete = 0
    for g in group_members:
        for member in g:
            if not isinstance(member, dict):
                total_members += 1
                continue
            total_members += 1
            has_all = True
            for field_name, variants in required_fields_variants.items():
                found = False
                for v in variants:
                    if v in member and member[v] not in (None, "", "null"):
                        found = True
                        break
                if not found:
                    has_all = False
                    break
            if has_all:
                fields_complete += 1

    if total_members > 0:
        completeness_ratio = fields_complete / total_members
        # Easy: >= 80% is full score, >= 60% is partial
        if completeness_ratio >= 0.80:
            scores["field_completeness_easy"] = 1.0
        elif completeness_ratio >= 0.60:
            scores["field_completeness_easy"] = 0.6
        else:
            scores["field_completeness_easy"] = 0.2 if completeness_ratio > 0 else 0.0
    else:
        scores["field_completeness_easy"] = 0.0

    # ===== EASY HIDDEN: Phone format valid =====
    # Phone numbers should be 11-digit Chinese mobile numbers (format only)
    phone_format_checks = 0
    phone_format_ok = 0
    for g in group_members:
        for member in g:
            if not isinstance(member, dict):
                continue
            phone = extract_phone(member)
            if phone and phone not in ("None", "null", ""):
                phone_format_checks += 1
                # Chinese mobile: 11 digits starting with 1
                cleaned = re.sub(r"[\s\-]", "", phone)
                if re.match(r"^1\d{10}$", cleaned):
                    phone_format_ok += 1
    if phone_format_checks > 0:
        fmt_ratio = phone_format_ok / phone_format_checks
        scores["phone_format_valid"] = 1.0 if fmt_ratio >= 0.90 else (0.5 if fmt_ratio >= 0.70 else 0.0)
    else:
        scores["phone_format_valid"] = 0.0

    # ===== HARD HIDDEN: Phone accuracy (exact match to CSV) =====
    phone_checks = 0
    phone_correct = 0
    for g in group_members:
        for member in g:
            if not isinstance(member, dict):
                continue
            name = extract_name(member)
            phone = extract_phone(member)
            if name in student_by_name and phone and phone not in ("None", "null", ""):
                phone_checks += 1
                actual_phone = student_by_name[name].get("手机号码", "").strip()
                if phone == actual_phone:
                    phone_correct += 1
    if phone_checks > 0:
        scores["phone_accuracy_exact"] = round(phone_correct / phone_checks, 4)
    else:
        scores["phone_accuracy_exact"] = 0.0

    # ===== HARD HIDDEN: Age data accuracy =====
    # Ages in grouping output must exactly match CSV for each student
    age_checks = 0
    age_correct = 0
    for g in group_members:
        for member in g:
            if not isinstance(member, dict):
                continue
            name = extract_name(member)
            reported_age = extract_age(member)
            if name in student_by_name and reported_age is not None:
                age_checks += 1
                try:
                    actual_age = int(student_by_name[name].get("年龄", 0))
                except (ValueError, TypeError):
                    actual_age = 0
                if reported_age == actual_age:
                    age_correct += 1
    if age_checks > 0:
        scores["age_data_accuracy"] = round(age_correct / age_checks, 4)
    else:
        scores["age_data_accuracy"] = 0.0

    # Constraint 1: 黄高丽, 符群丽, 楼静 must be in the same group
    specified = {"黄高丽", "符群丽", "楼静"}
    specified_same = 0.0
    for names in group_names:
        found = specified & set(names)
        if len(found) == 3:
            specified_same = 1.0
            break
        elif len(found) == 2:
            specified_same = 0.3
    scores["specified_together"] = specified_same

    # Constraint 2: Group sizes should be 11, 11, 11, 12
    sizes = sorted([len(g) for g in group_names])
    expected_sizes = [11, 11, 11, 12]
    if sizes == expected_sizes:
        scores["group_sizes"] = 1.0
    elif all(10 <= s <= 13 for s in sizes) and sum(sizes) == 45:
        scores["group_sizes"] = 0.5
    elif sum(sizes) == 45:
        scores["group_sizes"] = 0.2
    else:
        scores["group_sizes"] = 0.0

    # Constraint 3: Youth (16-30) should be evenly distributed
    student_ages = {s["姓名"].strip(): int(s.get("年龄", 0)) for s in students if s.get("姓名")}
    youth_per_group = []
    for names in group_names:
        youth_count = sum(1 for n in names if student_ages.get(n, 99) <= 30)
        youth_per_group.append(youth_count)

    if len(youth_per_group) == 4:
        max_youth = max(youth_per_group) if youth_per_group else 0
        min_youth = min(youth_per_group) if youth_per_group else 0
        if max_youth - min_youth <= 1 and sum(youth_per_group) >= 8:
            scores["youth_distribution"] = 1.0
        elif max_youth - min_youth <= 1 and sum(youth_per_group) >= 6:
            scores["youth_distribution"] = 0.7
        elif max_youth - min_youth <= 2 and sum(youth_per_group) >= 6:
            scores["youth_distribution"] = 0.4
        elif sum(youth_per_group) >= 4:
            scores["youth_distribution"] = 0.2
        else:
            scores["youth_distribution"] = 0.0
    else:
        scores["youth_distribution"] = 0.0

    # Constraint 4: Age balance across groups
    avg_ages = []
    for names in group_names:
        ages = [student_ages.get(n, 0) for n in names if student_ages.get(n, 0) > 0]
        if ages:
            avg_ages.append(sum(ages) / len(ages))
    if len(avg_ages) >= 4:
        age_range = max(avg_ages) - min(avg_ages)
        if age_range <= 2.0:
            scores["age_balance"] = 1.0
        elif age_range <= 4.0:
            scores["age_balance"] = 0.6
        elif age_range <= 6.0:
            scores["age_balance"] = 0.3
        else:
            scores["age_balance"] = 0.1
    else:
        scores["age_balance"] = 0.0

    return scores


def grade_workspace(ws: Path) -> dict:
    """Main grading function."""
    # Load student data
    csv_path = ws / "fixtures" / "training_data" / "students.csv"
    if not csv_path.exists():
        csv_path = ws / "training_data" / "students.csv"
    students = _load_csv(csv_path)

    # Load outputs
    output_dir = ws / "output"
    profile_path = output_dir / "profile_analysis.json"
    grouping_path = output_dir / "grouping_result.json"

    profile = _load_json(profile_path)
    grouping = _load_json(grouping_path)

    components: dict[str, float] = {}

    # Check profile analysis
    if profile and isinstance(profile, dict):
        profile_scores = _check_profile(profile, students)
        components["profile_gender"] = profile_scores.get("gender_distribution", 0.0)
        components["profile_gender_pct"] = profile_scores.get("gender_percentage", 0.0)
        components["profile_age"] = profile_scores.get("age_distribution", 0.0)
        components["profile_avg_age"] = profile_scores.get("average_age", 0.0)
        components["profile_location"] = profile_scores.get("location_distribution", 0.0)
        components["profile_industry"] = profile_scores.get("industry_distribution", 0.0)
        components["profile_industry_counts"] = profile_scores.get("industry_counts_exact", 0.0)
    else:
        components["profile_gender"] = 0.0
        components["profile_gender_pct"] = 0.0
        components["profile_age"] = 0.0
        components["profile_avg_age"] = 0.0
        components["profile_location"] = 0.0
        components["profile_industry"] = 0.0
        components["profile_industry_counts"] = 0.0

    # Check grouping
    if grouping:
        grouping_scores = _check_grouping(grouping, students)
        components["group_structure"] = grouping_scores.get("group_structure", 0.0)
        components["specified_together"] = grouping_scores.get("specified_together", 0.0)
        components["group_sizes"] = grouping_scores.get("group_sizes", 0.0)
        components["youth_distribution"] = grouping_scores.get("youth_distribution", 0.0)
        components["age_balance"] = grouping_scores.get("age_balance", 0.0)
        # Easy hidden checks
        components["data_integrity_easy"] = grouping_scores.get("data_integrity_easy", 0.0)
        components["field_completeness_easy"] = grouping_scores.get("field_completeness_easy", 0.0)
        components["phone_format_valid"] = grouping_scores.get("phone_format_valid", 0.0)
        # Hard hidden checks
        components["data_integrity_strict"] = grouping_scores.get("data_integrity_strict", 0.0)
        components["phone_accuracy_exact"] = grouping_scores.get("phone_accuracy_exact", 0.0)
        components["age_data_accuracy"] = grouping_scores.get("age_data_accuracy", 0.0)
    else:
        components["group_structure"] = 0.0
        components["specified_together"] = 0.0
        components["group_sizes"] = 0.0
        components["youth_distribution"] = 0.0
        components["age_balance"] = 0.0
        components["data_integrity_easy"] = 0.0
        components["field_completeness_easy"] = 0.0
        components["phone_format_valid"] = 0.0
        components["data_integrity_strict"] = 0.0
        components["phone_accuracy_exact"] = 0.0
        components["age_data_accuracy"] = 0.0

    # ---------------------------------------------------------------
    # Weight design:
    #   Visible checks (profile + grouping constraints): 65%
    #   Hidden checks (easy + hard tiers):              35%
    #     - Easy tier  (all agents should pass): 12%
    #     - Hard tier  (only strong agents pass): 23%
    # ---------------------------------------------------------------
    weights = {
        # --- Visible: Profile analysis (20%) ---
        "profile_gender": 0.04,
        "profile_age": 0.05,
        "profile_avg_age": 0.03,
        "profile_location": 0.04,
        "profile_industry": 0.04,
        # --- Visible: Grouping constraints (45%) ---
        "group_structure": 0.05,
        "specified_together": 0.12,
        "group_sizes": 0.10,
        "youth_distribution": 0.08,
        "age_balance": 0.10,
        # --- Hidden EASY tier (12%) ---
        "data_integrity_easy": 0.04,       # lenient: >=40/45 students present
        "field_completeness_easy": 0.04,   # lenient: >=80% members have all fields
        "phone_format_valid": 0.04,        # lenient: phone numbers are 11 digits
        # --- Hidden HARD tier (23%) ---
        "data_integrity_strict": 0.06,     # strict: all 45 exactly once, 0 errors
        "phone_accuracy_exact": 0.06,      # strict: phone numbers match CSV exactly
        "age_data_accuracy": 0.05,         # strict: ages in output match CSV exactly
        "profile_gender_pct": 0.03,        # strict: percentage calculation correct
        "profile_industry_counts": 0.03,   # strict: industry counts exact
    }

    # Verify weights sum to ~1.0
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 0.01, f"Weights sum: {total_weight}"

    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "tier_summary": {
            "visible": round(sum(weights[k] * components[k] for k in [
                "profile_gender", "profile_age", "profile_avg_age",
                "profile_location", "profile_industry",
                "group_structure", "specified_together", "group_sizes",
                "youth_distribution", "age_balance",
            ]), 4),
            "hidden_easy": round(sum(weights[k] * components[k] for k in [
                "data_integrity_easy", "field_completeness_easy", "phone_format_valid",
            ]), 4),
            "hidden_hard": round(sum(weights[k] * components[k] for k in [
                "data_integrity_strict", "phone_accuracy_exact", "age_data_accuracy",
                "profile_gender_pct", "profile_industry_counts",
            ]), 4),
        },
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
