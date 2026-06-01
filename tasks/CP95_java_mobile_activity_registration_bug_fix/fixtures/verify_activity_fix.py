"""Hidden verifier for CP93 — Java mobile activity registration multi-bug fix."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    base = ws / "src" / "main" / "java" / "com" / "tongtech" / "smzy" / "areaSpace" / "jingan"
    impl_file = base / "service" / "impl" / "JaSjkjActivityMobileServiceImpl.java"
    ctrl_file = base / "controller" / "JaSjkjActivityMobileController.java"
    mapper_xml = base / "mapper" / "JaSjkjActivityMapper.xml"

    components = {k: 0.0 for k in [
        "mobile_filters_expired", "userid_from_userinfo",
        "check_register_endpoint", "detail_with_registration",
        "contact_phone_decrypt",
    ]}

    for f in [impl_file, ctrl_file, mapper_xml]:
        if f.exists():
            c = _read(f)
            if re.search(r"status\s*!=\s*2|status.*expired|expire|!.*status.*2|过期", c, re.I):
                components["mobile_filters_expired"] = 1.0
                break
            if re.search(r"setStatus.*[01]|dto\.setStatus|NOW\(\)|CURDATE|end_time.*>", c, re.I):
                components["mobile_filters_expired"] = 0.5
                break

    all_text = ""
    for f in [impl_file, ctrl_file]:
        if f.exists():
            all_text += _read(f)
    has_userinfo = bool(re.search(r"UserInfo|userInfo|getUser(Id|Info)|SecurityUtils|getLoginUser", all_text, re.I))
    still_dto = ("dto.getUserId()" in (_read(impl_file) if impl_file.exists() else "")) and ("register" in (_read(impl_file) if impl_file.exists() else ""))
    if has_userinfo and not still_dto:
        components["userid_from_userinfo"] = 1.0
    elif has_userinfo:
        components["userid_from_userinfo"] = 0.5

    if ctrl_file.exists():
        c = _read(ctrl_file)
        has_check = bool(re.search(r"checkRegist|check.*[Rr]egist|/check", c))
        has_codes = False
        for f in [impl_file, ctrl_file]:
            if f.exists() and re.search(r"return\s+[012]|result\s*=\s*[012]|status.*[012]|满员|已满|已关闭|已报名|48.*小时|48.*hour", _read(f), re.I):
                has_codes = True
                break
        if has_check and has_codes:
            components["check_register_endpoint"] = 1.0
        elif has_check:
            components["check_register_endpoint"] = 0.5
        elif has_codes:
            components["check_register_endpoint"] = 0.25

    if ctrl_file.exists():
        c = _read(ctrl_file)
        has_detail = bool(re.search(r"/detail|detail\(|getDetail|getActivity", c))
        has_reg_info = False
        for f in [impl_file, ctrl_file]:
            if f.exists() and re.search(r"isRegistered|registr.*info|selectRegistration|报名.*信息", _read(f), re.I):
                has_reg_info = True
                break
        if has_detail and has_reg_info:
            components["detail_with_registration"] = 1.0
        elif has_detail:
            components["detail_with_registration"] = 0.5

    decrypt_score = 0.0
    for f in [impl_file, ctrl_file]:
        if f.exists():
            c = _read(f)
            has_aes = bool(re.search(r"AES|aes|decrypt|解密", c))
            has_contact = "contactPhone" in c or "contact_phone" in c
            if has_aes and has_contact:
                decrypt_score = 1.0
                break
            if has_aes:
                decrypt_score = max(decrypt_score, 0.5)
    components["contact_phone_decrypt"] = decrypt_score

    weights = {
        "mobile_filters_expired": 0.20,
        "userid_from_userinfo": 0.20,
        "check_register_endpoint": 0.20,
        "detail_with_registration": 0.20,
        "contact_phone_decrypt": 0.20,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    print(json.dumps(grade_workspace(Path("/workspace")), ensure_ascii=False))


if __name__ == "__main__":
    main()
