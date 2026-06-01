"""Hidden verifier for CP155 — Full-Stack Add Field Across Layers.

Checks that 'profile_signature' field has been properly added across:
1. Model layer (SQLAlchemy column)
2. DTO/Schema layer (Pydantic schemas: create, update, response)
3. Service layer (create_user and update_user handle the field)
4. Frontend form (input/display for the signature field)
5. Quality: URL validation, nullable consistency, conditional update pattern
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, name: str) -> Path | None:
    """Find a file by name, checking common locations."""
    direct = base / name
    if direct.exists():
        return direct
    for p in base.rglob(name):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    # Try both possible locations
    app_dir = ws / "fixtures" / "user-management-app"
    if not app_dir.exists():
        app_dir = ws / "user-management-app"
    if not app_dir.exists():
        # Search for it
        for candidate in ws.rglob("models.py"):
            if "user-management-app" in str(candidate):
                app_dir = candidate.parent
                break

    components = {k: 0.0 for k in [
        "model_column_added",
        "schema_create_field",
        "schema_update_field",
        "schema_response_field",
        "service_create_handles",
        "service_update_handles",
        "form_has_input",
        "model_to_dict_includes",
        # --- Hidden harder checks ---
        "schema_url_validation",
        "model_column_length_match",
        "service_update_conditional_pattern",
        "form_xss_safe_preview",
        "schema_update_optional_explicit",
        # --- Additional hidden checks (harder) ---
        "form_value_binding_on_edit",
        "service_create_kwarg_pattern",
        "response_schema_optional_with_default",
    ]}

    # 1. Model: Check SQLAlchemy column for profile_signature
    models_file = _find_file(app_dir, "models.py")
    models_content = ""
    if models_file:
        models_content = _read(models_file)
        # Must have a db.Column definition for profile_signature
        has_column = bool(re.search(
            r'profile_signature\s*=\s*db\.Column\s*\(\s*db\.String',
            models_content
        ))
        # Also accept Text type
        if not has_column:
            has_column = bool(re.search(
                r'profile_signature\s*=\s*db\.Column\s*\(\s*db\.Text',
                models_content
            ))
        components["model_column_added"] = 1.0 if has_column else 0.0

        # Check to_dict includes the field
        to_dict_match = re.search(r'def\s+to_dict\s*\(self\).*?(?=\n    def |\nclass |\Z)', models_content, re.DOTALL)
        if to_dict_match:
            to_dict_body = to_dict_match.group(0)
            has_in_dict = "profile_signature" in to_dict_body
            components["model_to_dict_includes"] = 1.0 if has_in_dict else 0.0
        else:
            if "profile_signature" in models_content and "to_dict" in models_content:
                components["model_to_dict_includes"] = 0.5

        # HIDDEN CHECK: Column length should be specified (not unbounded String)
        # Strong models match the existing avatar_url pattern: db.String(512)
        has_length_spec = bool(re.search(
            r'profile_signature\s*=\s*db\.Column\s*\(\s*db\.String\s*\(\s*\d+\s*\)',
            models_content
        ))
        # Extra credit for nullable=True being explicit (matching existing patterns)
        has_nullable = bool(re.search(
            r'profile_signature\s*=\s*db\.Column\s*\(.*?nullable\s*=\s*True',
            models_content
        ))
        if has_length_spec and has_nullable:
            components["model_column_length_match"] = 1.0
        elif has_length_spec:
            components["model_column_length_match"] = 0.6
        elif has_nullable:
            components["model_column_length_match"] = 0.3
        else:
            components["model_column_length_match"] = 0.0

    # 2. Schemas: Check Pydantic schemas
    schemas_file = _find_file(app_dir, "schemas.py")
    schemas_content = ""
    if schemas_file:
        schemas_content = _read(schemas_file)

        # Check UserCreateSchema has profile_signature
        create_match = re.search(
            r'class\s+UserCreateSchema.*?(?=\nclass |\Z)', schemas_content, re.DOTALL
        )
        if create_match:
            create_body = create_match.group(0)
            has_field = "profile_signature" in create_body
            components["schema_create_field"] = 1.0 if has_field else 0.0

            # HIDDEN sub-check: field should be Optional in create schema
            # (a signature URL is not required when creating a user, matches avatar_url pattern)
            create_field_optional = bool(re.search(
                r'profile_signature\s*:\s*(?:Optional\s*\[|str\s*\|\s*None)',
                create_body
            ))
            # If the field is present but NOT optional, it's a design mistake
            # that would break existing user creation flows
            if has_field and not create_field_optional:
                components["schema_create_field"] = 0.4  # penalize required field

        # Check UserUpdateSchema has profile_signature
        update_match = re.search(
            r'class\s+UserUpdateSchema.*?(?=\nclass |\Z)', schemas_content, re.DOTALL
        )
        if update_match:
            update_body = update_match.group(0)
            has_field = "profile_signature" in update_body
            components["schema_update_field"] = 1.0 if has_field else 0.0

            # HIDDEN CHECK: Update schema field must be explicitly Optional
            # (not just having a default=None without Optional type annotation)
            # Accept both Optional[str] and str | None syntax
            has_optional_explicit = bool(re.search(
                r'profile_signature\s*:\s*(?:Optional\s*\[|str\s*\|\s*None)',
                update_body
            ))
            components["schema_update_optional_explicit"] = 1.0 if has_optional_explicit else 0.0

        # Check UserResponseSchema has profile_signature
        response_match = re.search(
            r'class\s+UserResponseSchema.*?(?=\nclass |\Z)', schemas_content, re.DOTALL
        )
        if response_match:
            response_body = response_match.group(0)
            has_field = "profile_signature" in response_body
            components["schema_response_field"] = 1.0 if has_field else 0.0

        # HIDDEN CHECK: URL validation — check for any URL validation on profile_signature
        # Good agents add a validator, HttpUrl type, or field constraint for URL format
        has_url_validation = False
        # Check for HttpUrl type annotation
        if re.search(r'profile_signature\s*:\s*.*?(?:HttpUrl|AnyUrl|AnyHttpUrl)', schemas_content):
            has_url_validation = True
        # Check for a @validator or @field_validator for profile_signature
        if re.search(r'@(?:validator|field_validator)\s*\(\s*["\']profile_signature["\']', schemas_content):
            has_url_validation = True
        # Check for pattern/regex constraint on the field
        if re.search(r'profile_signature.*?(?:pattern|regex)\s*=', schemas_content):
            has_url_validation = True
        # Check for max_length on the field (weaker but shows awareness)
        has_max_length = bool(re.search(
            r'profile_signature.*?max_length\s*=\s*\d+', schemas_content
        ))
        if has_url_validation:
            components["schema_url_validation"] = 1.0
        elif has_max_length:
            components["schema_url_validation"] = 0.4
        else:
            components["schema_url_validation"] = 0.0

    # 3. Service: Check create_user and update_user handle the field
    services_file = _find_file(app_dir, "services.py")
    if services_file:
        services_content = _read(services_file)

        # Check create_user assigns profile_signature
        create_match = re.search(
            r'def\s+create_user.*?(?=\n    @|\n    def |\nclass |\Z)', services_content, re.DOTALL
        )
        if create_match:
            create_body = create_match.group(0)
            has_assign = "profile_signature" in create_body
            components["service_create_handles"] = 1.0 if has_assign else 0.0

        # Check update_user assigns profile_signature
        update_match = re.search(
            r'def\s+update_user.*?(?=\n    @|\n    def |\nclass |\Z)', services_content, re.DOTALL
        )
        if update_match:
            update_body = update_match.group(0)
            has_assign = "profile_signature" in update_body
            components["service_update_handles"] = 1.0 if has_assign else 0.0

            # HIDDEN CHECK: Conditional update pattern —
            # The update should use "if data.profile_signature is not None" pattern
            # (matching the existing pattern in the codebase), NOT unconditional assignment.
            # This prevents clearing the field when it's not provided in the update payload.
            has_conditional = bool(re.search(
                r'if\s+data\.profile_signature\s+is\s+not\s+None',
                update_body
            ))
            # Also accept hasattr pattern or getattr with sentinel
            if not has_conditional:
                has_conditional = bool(re.search(
                    r'if\s+.*?profile_signature.*?is\s+not\s+None',
                    update_body
                ))
            components["service_update_conditional_pattern"] = 1.0 if has_conditional else 0.0

    # 4. Frontend form: Check template has input for profile_signature
    form_file = _find_file(app_dir / "templates", "user_form.html")
    if not form_file:
        for candidate in app_dir.rglob("user_form.html"):
            form_file = candidate
            break
    if form_file:
        form_content = _read(form_file)
        # Check for input field related to profile_signature
        has_input = bool(re.search(
            r'(name|id)\s*=\s*["\']profile_signature["\']', form_content
        ))
        # Also check for label/display mentioning signature
        has_label = bool(re.search(
            r'(电子签名|签名|signature)', form_content, re.IGNORECASE
        ))
        # Check for image preview capability
        has_preview = bool(re.search(
            r'profile_signature.*?<img|<img.*?profile_signature|preview.*?signature|signature.*?preview',
            form_content, re.IGNORECASE | re.DOTALL
        ))
        score = 0.0
        if has_input:
            score += 0.5
        if has_label:
            score += 0.25
        if has_preview:
            score += 0.25
        components["form_has_input"] = min(score, 1.0)

        # HIDDEN CHECK: XSS-safe preview — the img src should not be raw unescaped.
        # Good solutions use conditional rendering ({% if ... %}) and/or proper escaping.
        # They should also handle the case where profile_signature is empty/None.
        xss_score = 0.0
        # Check that img tag is inside a conditional block (not always rendered)
        has_conditional_img = bool(re.search(
            r'\{%\s*if\s+.*?profile_signature.*?%\}.*?<img.*?profile_signature.*?\{%\s*endif\s*%\}',
            form_content, re.DOTALL | re.IGNORECASE
        ))
        if has_conditional_img:
            xss_score += 0.5
        # Check that the URL input has type="url" (provides browser-level validation)
        has_url_type = bool(re.search(
            r'<input[^>]*name\s*=\s*["\']profile_signature["\'][^>]*type\s*=\s*["\']url["\']|'
            r'<input[^>]*type\s*=\s*["\']url["\'][^>]*name\s*=\s*["\']profile_signature["\']',
            form_content, re.IGNORECASE
        ))
        if has_url_type:
            xss_score += 0.5
        else:
            # Partial credit for type="text" with placeholder hinting URL
            has_url_placeholder = bool(re.search(
                r'profile_signature.*?placeholder\s*=\s*["\'].*?(?:http|url|https)',
                form_content, re.IGNORECASE | re.DOTALL
            ))
            if has_url_placeholder:
                xss_score += 0.2
        components["form_xss_safe_preview"] = min(xss_score, 1.0)

        # HIDDEN CHECK: Value binding on edit — the input should display the
        # existing profile_signature value when editing a user.
        # The existing avatar_url pattern is: value="{{ user.avatar_url if user else '' }}"
        # Weak agents add the input but forget to bind the value for edit mode.
        has_value_binding = bool(re.search(
            r'name\s*=\s*["\']profile_signature["\'][^>]*value\s*=\s*["\'].*?'
            r'(?:user\.profile_signature|user\[.profile_signature.\])',
            form_content, re.IGNORECASE | re.DOTALL
        ))
        if not has_value_binding:
            # Also check reverse order (value before name)
            has_value_binding = bool(re.search(
                r'value\s*=\s*["\'].*?(?:user\.profile_signature|user\[.profile_signature.\])'
                r'[^>]*name\s*=\s*["\']profile_signature["\']',
                form_content, re.IGNORECASE | re.DOTALL
            ))
        if not has_value_binding:
            # Check for Jinja2 expression with profile_signature in a value attr
            # near an input with the correct name
            has_value_binding = bool(re.search(
                r'profile_signature.*?value\s*=\s*["\']\{\{.*?profile_signature',
                form_content, re.IGNORECASE | re.DOTALL
            ))
        components["form_value_binding_on_edit"] = 1.0 if has_value_binding else 0.0

    # 5. Service: create_user keyword argument pattern check
    if services_file:
        services_content = _read(services_file)
        # HIDDEN CHECK: The create_user method should pass profile_signature as
        # a keyword argument to User() matching the existing pattern exactly:
        #   profile_signature=data.profile_signature
        # Weak agents might use setattr(), a dict spread, or miss it entirely.
        # We also check it appears INSIDE the User() constructor call, not after.
        create_fn_match = re.search(
            r'def\s+create_user.*?(?=\n    @|\n    def |\nclass |\Z)',
            services_content, re.DOTALL
        )
        if create_fn_match:
            create_fn_body = create_fn_match.group(0)
            # Check for explicit keyword arg in User() constructor
            user_constructor = re.search(
                r'User\s*\((.*?)\)', create_fn_body, re.DOTALL
            )
            if user_constructor:
                constructor_args = user_constructor.group(1)
                has_kwarg = bool(re.search(
                    r'profile_signature\s*=\s*data\.profile_signature',
                    constructor_args
                ))
                components["service_create_kwarg_pattern"] = 1.0 if has_kwarg else 0.0
            else:
                # No User() constructor found — likely broken, score 0
                components["service_create_kwarg_pattern"] = 0.0
        else:
            components["service_create_kwarg_pattern"] = 0.0

    # 6. Response schema: profile_signature should be Optional with default None
    if schemas_file:
        schemas_content_recheck = _read(schemas_file)
        response_match2 = re.search(
            r'class\s+UserResponseSchema.*?(?=\nclass |\Z)',
            schemas_content_recheck, re.DOTALL
        )
        if response_match2:
            resp_body = response_match2.group(0)
            # HIDDEN CHECK: In UserResponseSchema, profile_signature must be
            # Optional[str] = None (or str | None = None). If the field is added
            # without a default, existing users without the field will cause
            # serialization failures. A strong agent recognizes this from the
            # avatar_url pattern. A weak agent may just add `profile_signature: str`.
            has_optional_default = bool(re.search(
                r'profile_signature\s*:\s*(?:Optional\s*\[\s*str\s*\]|str\s*\|\s*None)\s*=\s*None',
                resp_body
            ))
            if has_optional_default:
                components["response_schema_optional_with_default"] = 1.0
            else:
                # Partial credit: at least Optional annotation even without = None
                has_optional_no_default = bool(re.search(
                    r'profile_signature\s*:\s*(?:Optional\s*\[\s*str\s*\]|str\s*\|\s*None)',
                    resp_body
                ))
                if has_optional_no_default:
                    components["response_schema_optional_with_default"] = 0.5
                else:
                    # Check if field exists at all (just str, no Optional)
                    has_field_any = "profile_signature" in resp_body
                    components["response_schema_optional_with_default"] = 0.1 if has_field_any else 0.0

    # Calculate overall score with rebalanced weights
    # Basic checks (reduced weight): 35%
    # Hidden quality checks (harder): 65%
    weights = {
        # Basic existence checks — 35% total
        "model_column_added": 0.06,
        "schema_create_field": 0.04,
        "schema_update_field": 0.04,
        "schema_response_field": 0.04,
        "service_create_handles": 0.05,
        "service_update_handles": 0.04,
        "form_has_input": 0.04,
        "model_to_dict_includes": 0.04,
        # Hidden quality checks — 65% total
        "schema_url_validation": 0.12,
        "model_column_length_match": 0.07,
        "service_update_conditional_pattern": 0.08,
        "form_xss_safe_preview": 0.11,
        "schema_update_optional_explicit": 0.07,
        # Additional hidden checks (harder)
        "form_value_binding_on_edit": 0.08,
        "service_create_kwarg_pattern": 0.05,
        "response_schema_optional_with_default": 0.07,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    result = grade_workspace(ws)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
