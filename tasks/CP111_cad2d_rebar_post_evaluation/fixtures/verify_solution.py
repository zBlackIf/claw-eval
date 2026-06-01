"""Hidden verifier for CP111 - CAD 2D Rebar Post-Evaluation System."""
from __future__ import annotations

import json
import sys
import math
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_file(base: Path, pattern: str) -> Path | None:
    """Find a file matching pattern recursively."""
    for p in base.rglob(pattern):
        return p
    return None


def grade_workspace(ws: Path) -> dict:
    """Grade the workspace for correct post-evaluation implementation."""

    # Look in multiple possible locations
    cad_base = ws / "cad2d_base"
    if not cad_base.exists():
        cad_base = ws / "fixtures" / "cad2d_base"

    components = {k: 0.0 for k in [
        "evaluate_function_exists",
        "inside_contour_check",
        "anchor_angle_check",
        "anchor_clearance_check",
        "spacing_check",
        "returns_structured_result",
        "handles_test_layout",
        "identifies_specific_violations",
        "edge_case_robustness",
        "numerical_accuracy",
        "false_positive_avoidance",
        "contour_containment_correctness",
        "anchor_length_validation",
    ]}

    # 1. Check that evaluate_rebar_layout function exists
    eval_file = None
    eval_content = ""
    for candidate in ["evaluation.py", "post_evaluation.py", "validator.py",
                      "checker.py", "evaluator.py", "eval.py"]:
        found = _find_file(cad_base, candidate)
        if found:
            content = _read(found)
            if "evaluate_rebar_layout" in content or "evaluate_layout" in content:
                eval_file = found
                eval_content = content
                break

    if not eval_file:
        for py_file in cad_base.rglob("*.py"):
            content = _read(py_file)
            if "def evaluate_rebar_layout" in content or "def evaluate_layout" in content:
                eval_file = py_file
                eval_content = content
                break

    if eval_file:
        has_func = ("def evaluate_rebar_layout" in eval_content or
                    "def evaluate_layout" in eval_content)
        has_params = ("contour" in eval_content and "stirrup" in eval_content)
        components["evaluate_function_exists"] = 1.0 if (has_func and has_params) else (0.5 if has_func else 0.0)
    else:
        components["evaluate_function_exists"] = 0.0

    # 2. Check for inside-contour validation (point-in-polygon check)
    if eval_content:
        has_inside = any(kw in eval_content for kw in [
            "inside", "in_polygon", "point_in", "contains",
            "within", "inside_contour",
        ])
        has_cover = "cover" in eval_content
        has_offset = any(kw in eval_content for kw in ["offset", "shrink", "inset", "inner"])
        components["inside_contour_check"] = (
            1.0 if (has_inside and has_cover and has_offset) else
            0.6 if (has_inside and has_cover) else
            0.2 if has_inside else 0.0
        )

    # 3. Check for anchor angle validation
    if eval_content:
        has_angle = any(kw in eval_content for kw in [
            "angle", "anchor_angle", "bend_angle", "min_angle",
        ])
        has_90 = "90" in eval_content
        has_vector_math = any(kw in eval_content for kw in [
            "atan2", "acos", "dot", "cross",
        ])
        components["anchor_angle_check"] = (
            1.0 if (has_angle and has_90 and has_vector_math) else
            0.5 if (has_angle and has_90) else
            0.2 if has_angle else 0.0
        )

    # 4. Check for anchor-body clearance validation
    if eval_content:
        has_clearance = any(kw in eval_content for kw in [
            "clearance", "gap", "separation",
            "anchor_body", "body_distance", "min_dist",
        ])
        has_anchor_body = ("anchor" in eval_content and "body" in eval_content)
        # Check for point-to-segment or segment-to-segment distance calculation
        has_seg_dist = any(kw in eval_content for kw in [
            "point_to_segment", "segment_distance", "line_distance",
            "perpendicular", "project", "closest_point",
        ])
        components["anchor_clearance_check"] = (
            1.0 if (has_clearance and has_anchor_body and has_seg_dist) else
            0.5 if (has_clearance and has_anchor_body) else
            0.2 if has_clearance else 0.0
        )

    # 5. Check for spacing validation
    if eval_content:
        has_spacing = "spacing" in eval_content
        has_max_check = any(kw in eval_content for kw in [
            "max_spacing", "exceed",
        ])
        components["spacing_check"] = (
            1.0 if (has_spacing and has_max_check) else
            0.4 if has_spacing else 0.0
        )

    # 6. Check return structure
    if eval_content:
        has_passed = "'passed'" in eval_content or '"passed"' in eval_content
        has_checks = "'checks'" in eval_content or '"checks"' in eval_content
        has_name_field = "'name'" in eval_content or '"name"' in eval_content
        has_detail_field = "'detail'" in eval_content or '"detail"' in eval_content
        components["returns_structured_result"] = (
            1.0 if (has_passed and has_checks and has_name_field and has_detail_field) else
            0.5 if (has_passed and has_checks) else
            0.2 if has_passed else 0.0
        )

    # === RUNTIME CHECKS (the hard part - requires actual correctness) ===

    eval_func = None
    result = None
    try:
        sys.path.insert(0, str(ws))
        sys.path.insert(0, str(ws / "fixtures"))

        from cad2d_base.test_layout import get_test_layout
        layout = get_test_layout()

        # Try importing the evaluation function
        try:
            from cad2d_base.entities.evaluation import evaluate_rebar_layout
            eval_func = evaluate_rebar_layout
        except ImportError:
            try:
                from cad2d_base.entities import evaluate_rebar_layout
                eval_func = evaluate_rebar_layout
            except ImportError:
                try:
                    from cad2d_base.evaluation import evaluate_rebar_layout
                    eval_func = evaluate_rebar_layout
                except ImportError:
                    try:
                        from cad2d_base.entities.evaluation import evaluate_layout
                        eval_func = evaluate_layout
                    except ImportError:
                        pass

        if eval_func:
            result = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=layout['stirrups'],
                config=layout['config'],
            )

            # 7. Basic test layout handling
            if isinstance(result, dict):
                has_passed_key = 'passed' in result
                has_checks_key = 'checks' in result
                checks_list = result.get('checks', [])
                has_multiple_checks = len(checks_list) >= 3

                found_failures = False
                if not result.get('passed', True):
                    found_failures = True
                elif any(not c.get('passed', True) for c in checks_list):
                    found_failures = True

                components["handles_test_layout"] = (
                    1.0 if (has_passed_key and has_checks_key and has_multiple_checks and found_failures) else
                    0.5 if (has_passed_key and has_checks_key and has_multiple_checks) else
                    0.3 if (has_passed_key and has_checks_key) else
                    0.1 if isinstance(result, dict) else 0.0
                )
            else:
                components["handles_test_layout"] = 0.0

    except Exception:
        if eval_content:
            components["handles_test_layout"] = 0.05
        else:
            components["handles_test_layout"] = 0.0

    # 8. HIDDEN CHECK: Identifies SPECIFIC violations correctly
    # Strong models must correctly flag stirrup_0 (clearance) and stirrup_2 (angle)
    # AND must NOT false-flag stirrup_1 (which is correct)
    if eval_func and isinstance(result, dict):
        checks_list = result.get('checks', [])
        score_specific = 0.0

        # Look for per-stirrup or per-check detail that identifies which stirrup failed
        all_detail_text = " ".join(
            str(c.get('detail', '')) + str(c.get('name', ''))
            for c in checks_list
        ).lower()

        # Check if angle violation is identified (stirrup_2 specific)
        angle_checks = [c for c in checks_list if 'angle' in str(c.get('name', '')).lower()]
        clearance_checks = [c for c in checks_list if 'clearance' in str(c.get('name', '')).lower()
                           or 'distance' in str(c.get('name', '')).lower()
                           or 'gap' in str(c.get('name', '')).lower()]

        # Angle check must fail (stirrup_2 has acute angle)
        angle_failed = any(not c.get('passed', True) for c in angle_checks)
        # Clearance check must fail (stirrup_0 has clearance issue)
        clearance_failed = any(not c.get('passed', True) for c in clearance_checks)

        if angle_failed and clearance_failed:
            score_specific = 1.0
        elif angle_failed or clearance_failed:
            score_specific = 0.5
        elif not result.get('passed', True):
            # At least overall fails, but can't distinguish which checks
            score_specific = 0.2

        # Bonus: check if detail mentions specific stirrup indices or identifiable info
        if ('stirrup_0' in all_detail_text or 'stirrup[0]' in all_detail_text or
                '#0' in all_detail_text or 'index 0' in all_detail_text):
            score_specific = min(score_specific + 0.15, 1.0)
        if ('stirrup_2' in all_detail_text or 'stirrup[2]' in all_detail_text or
                '#2' in all_detail_text or 'index 2' in all_detail_text):
            score_specific = min(score_specific + 0.15, 1.0)

        components["identifies_specific_violations"] = round(score_specific, 4)

    # 9. HIDDEN CHECK: Edge case robustness
    # Test with edge cases that only a robust implementation handles
    if eval_func:
        from cad2d_base.geometry import Point2D, Wire2D
        from cad2d_base.entities import LineRebar

        edge_score = 0.0
        edge_tests_passed = 0
        edge_tests_total = 4

        # Edge case A: Empty stirrups list (should not crash, should pass)
        try:
            empty_result = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[],
                config=layout['config'],
            )
            if isinstance(empty_result, dict) and 'passed' in empty_result:
                edge_tests_passed += 1
        except Exception:
            pass

        # Edge case B: Empty dist_rebar_positions (should not crash)
        try:
            empty_dist_result = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=[],
                stirrups=layout['stirrups'],
                config=layout['config'],
            )
            if isinstance(empty_dist_result, dict) and 'passed' in empty_dist_result:
                edge_tests_passed += 1
        except Exception:
            pass

        # Edge case C: Stirrup with no anchors (anchor_start_count=0, anchor_end_count=0)
        try:
            no_anchor_rebar = LineRebar(
                points=[Point2D(100, 100), Point2D(500, 100), Point2D(500, 500), Point2D(100, 500)],
                diameter=8.0,
                anchor_start_count=0,
                anchor_end_count=0,
            )
            no_anchor_result = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[no_anchor_rebar],
                config=layout['config'],
            )
            if isinstance(no_anchor_result, dict) and 'passed' in no_anchor_result:
                edge_tests_passed += 1
        except Exception:
            pass

        # Edge case D: Config with extreme values (very tight clearance)
        try:
            tight_config = dict(layout['config'])
            tight_config['min_anchor_clearance'] = 100.0  # very large clearance requirement
            tight_result = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=layout['stirrups'],
                config=tight_config,
            )
            if isinstance(tight_result, dict) and 'passed' in tight_result:
                # With 100mm clearance requirement, at least some should fail
                if not tight_result.get('passed', True):
                    edge_tests_passed += 1
                else:
                    # Implementation ignores config value - partial credit
                    edge_tests_passed += 0  # no credit
        except Exception:
            pass

        components["edge_case_robustness"] = round(edge_tests_passed / edge_tests_total, 4)

    # 10. HIDDEN CHECK: Numerical accuracy
    # Verify the implementation computes geometrically correct values
    # Uses 3-point anchors where the bend point is clearly interior to the anchor,
    # avoiding ambiguity about shared junction points in the data structure.
    if eval_func and isinstance(result, dict):
        from cad2d_base.geometry import Point2D, Wire2D
        from cad2d_base.entities import LineRebar

        accuracy_tests = 0
        accuracy_total = 3

        # Accuracy test A: Stirrup with clear 90+ degree bend in anchor should PASS
        # 3-point anchor: tip -> bend -> junction, with 90-degree bend at middle point
        # Then body starts at junction and goes in same direction as last anchor segment
        try:
            # Anchor: goes down from (500,200) to (500,500) then right to (700,500)
            # Body starts at (700,500) and continues right -> angle at (500,500) is 90 degrees
            anchor_start_a = [Point2D(500, 200), Point2D(500, 500), Point2D(700, 500)]
            body_a = [Point2D(700, 500), Point2D(1200, 500), Point2D(1200, 1000), Point2D(500, 1000)]
            pts_a = anchor_start_a + body_a
            stirrup_a = LineRebar(
                points=pts_a, diameter=8.0,
                anchor_start_count=len(anchor_start_a), anchor_end_count=0,
            )
            result_a = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[stirrup_a],
                config=layout['config'],
            )
            if isinstance(result_a, dict):
                checks_a = result_a.get('checks', [])
                angle_checks_a = [c for c in checks_a if 'angle' in str(c.get('name', '')).lower()]
                # Should pass - bend angle is 90 degrees (acceptable)
                if angle_checks_a and all(c.get('passed', False) for c in angle_checks_a):
                    accuracy_tests += 1
                elif not angle_checks_a and result_a.get('passed', False):
                    # No explicit angle check but overall passed - acceptable
                    accuracy_tests += 1
        except Exception:
            pass

        # Accuracy test B: Stirrup with acute bend (~30 deg) in anchor should FAIL angle check
        # 3-point anchor: nearly collinear with body => very small bend angle
        try:
            # Anchor: from (400,520) to (500,500) then body goes to (1200,500)
            # The vectors at bend point (500,500): incoming from (400,520) and outgoing to (1200,500)
            # incoming vector: (100, -20), outgoing vector: (700, 0)
            # angle between them: arctan is small, roughly 1.6 degrees - clearly < 90
            anchor_start_b = [Point2D(400, 520), Point2D(500, 500)]
            body_b = [Point2D(500, 500), Point2D(1200, 500), Point2D(1200, 1000), Point2D(500, 1000)]
            pts_b = anchor_start_b + body_b
            stirrup_b = LineRebar(
                points=pts_b, diameter=8.0,
                anchor_start_count=len(anchor_start_b), anchor_end_count=0,
            )
            result_b = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[stirrup_b],
                config=layout['config'],
            )
            if isinstance(result_b, dict):
                # Overall should fail (due to acute angle)
                if not result_b.get('passed', True):
                    accuracy_tests += 1
                else:
                    # Check specifically for angle failure
                    checks_b = result_b.get('checks', [])
                    angle_checks_b = [c for c in checks_b if 'angle' in str(c.get('name', '')).lower()]
                    if angle_checks_b and any(not c.get('passed', True) for c in angle_checks_b):
                        accuracy_tests += 1
        except Exception:
            pass

        # Accuracy test C: Stirrup with anchor folding back onto body should FAIL clearance
        # Anchor runs parallel to a body segment with only 5mm gap (< 16mm min)
        try:
            # 3-point anchor that folds back: tip at (700,505), bend at (500,505), junction at (500,500)
            # Body: (500,500) -> (1200,500) -> ...
            # Segment (700,505)-(500,505) is 5mm from segment (500,500)-(1200,500)
            anchor_start_c = [Point2D(700, 505), Point2D(500, 505), Point2D(500, 500)]
            body_c = [Point2D(500, 500), Point2D(1200, 500), Point2D(1200, 1000), Point2D(500, 1000)]
            pts_c = anchor_start_c + body_c
            stirrup_c = LineRebar(
                points=pts_c, diameter=8.0,
                anchor_start_count=len(anchor_start_c), anchor_end_count=0,
            )
            result_c = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[stirrup_c],
                config=layout['config'],
            )
            if isinstance(result_c, dict):
                # Should fail overall due to clearance violation (5mm < 16mm)
                if not result_c.get('passed', True):
                    accuracy_tests += 1
        except Exception:
            pass

        components["numerical_accuracy"] = round(accuracy_tests / accuracy_total, 4)

    # 11. HIDDEN CHECK: False positive avoidance
    # stirrup_1 is CORRECT (proper anchor direction, good clearance, proper angle).
    # A naive/buggy implementation may flag it incorrectly.
    # This check verifies the implementation does NOT produce false positives.
    if eval_func and isinstance(result, dict):
        checks_list = result.get('checks', [])
        fp_score = 0.0

        # Test stirrup_1 alone — it should PASS all checks
        try:
            from cad2d_base.test_layout import create_stirrups
            all_stirrups = create_stirrups(cover=40.0, diameter=8.0)
            stirrup_1_only = [all_stirrups[1]]

            result_s1 = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=stirrup_1_only,
                config=layout['config'],
            )
            if isinstance(result_s1, dict):
                s1_checks = result_s1.get('checks', [])
                # stirrup_1 should pass ALL checks
                if result_s1.get('passed', False):
                    fp_score = 1.0
                else:
                    # Partial: maybe only some checks wrongly fail
                    failed_checks = [c for c in s1_checks if not c.get('passed', True)]
                    # Penalize each false positive
                    if len(s1_checks) > 0:
                        fp_score = max(0.0, 1.0 - len(failed_checks) * 0.4)
                    else:
                        fp_score = 0.2
        except Exception:
            fp_score = 0.0

        # Additionally verify in the full result that stirrup_1 is not specifically flagged
        all_detail_text = " ".join(
            str(c.get('detail', '')) for c in checks_list
        ).lower()
        if 'stirrup_1' in all_detail_text or 'stirrup[1]' in all_detail_text or '#1' in all_detail_text:
            # If detail mentions stirrup_1 as a failure, penalize
            if any(('stirrup_1' in str(c.get('detail', '')).lower() or
                    '#1' in str(c.get('detail', '')).lower()) and
                   not c.get('passed', True) for c in checks_list):
                fp_score = max(0.0, fp_score - 0.3)

        components["false_positive_avoidance"] = round(fp_score, 4)

    # 12. HIDDEN CHECK: Contour containment correctness
    # Test that point-in-polygon logic actually works with the trapezoidal contour.
    # A point clearly outside should be detected; a point inside should pass.
    if eval_func:
        containment_score = 0.0
        containment_tests = 0
        containment_total = 3

        try:
            from cad2d_base.geometry import Point2D, Wire2D
            from cad2d_base.entities import LineRebar

            # Test A: Stirrup with points CLEARLY inside the contour (well within cover offset)
            # Should pass containment check
            inner_body = [
                Point2D(200, 200), Point2D(1000, 200),
                Point2D(1000, 800), Point2D(200, 800),
            ]
            inner_stirrup = LineRebar(points=inner_body, diameter=8.0,
                                     anchor_start_count=0, anchor_end_count=0)
            result_inner = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[inner_stirrup],
                config=layout['config'],
            )
            if isinstance(result_inner, dict):
                inner_checks = result_inner.get('checks', [])
                containment_checks = [c for c in inner_checks
                                      if any(kw in str(c.get('name', '')).lower()
                                             for kw in ['contour', 'inside', 'contain', 'within', 'cover'])]
                # Should PASS containment
                if containment_checks and all(c.get('passed', False) for c in containment_checks):
                    containment_tests += 1
                elif not containment_checks and result_inner.get('passed', False):
                    containment_tests += 1  # no explicit check but overall passes
        except Exception:
            pass

        try:
            # Test B: Stirrup with a point CLEARLY outside the contour (x=-500)
            # Should FAIL containment check
            outer_body = [
                Point2D(-500, 200), Point2D(200, 200),
                Point2D(200, 600), Point2D(-500, 600),
            ]
            outer_stirrup = LineRebar(points=outer_body, diameter=8.0,
                                     anchor_start_count=0, anchor_end_count=0)
            result_outer = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[outer_stirrup],
                config=layout['config'],
            )
            if isinstance(result_outer, dict):
                outer_checks = result_outer.get('checks', [])
                containment_checks = [c for c in outer_checks
                                      if any(kw in str(c.get('name', '')).lower()
                                             for kw in ['contour', 'inside', 'contain', 'within', 'cover'])]
                # Should FAIL containment
                if containment_checks and any(not c.get('passed', True) for c in containment_checks):
                    containment_tests += 1
                elif not result_outer.get('passed', True):
                    containment_tests += 1  # overall fails
        except Exception:
            pass

        try:
            # Test C: Stirrup near the sloped edge of trapezoidal contour
            # Top of contour: from (130, 1800) to (1800, 1800). A point at (50, 1750) is
            # outside or within cover of the sloped left edge. Tests proper slope handling.
            slope_body = [
                Point2D(50, 1600), Point2D(300, 1600),
                Point2D(300, 1750), Point2D(50, 1750),
            ]
            slope_stirrup = LineRebar(points=slope_body, diameter=8.0,
                                     anchor_start_count=0, anchor_end_count=0)
            result_slope = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[slope_stirrup],
                config=layout['config'],
            )
            if isinstance(result_slope, dict):
                # Point (50, 1750) is very close to or outside the left slope edge
                # (left edge goes from (0,0) to (130,1800))
                # At y=1750: x_edge = 130 * (1750/1800) ≈ 126.4
                # So x=50 is OUTSIDE the left edge. Should fail.
                if not result_slope.get('passed', True):
                    containment_tests += 1
                else:
                    slope_checks = result_slope.get('checks', [])
                    containment_slope = [c for c in slope_checks
                                         if any(kw in str(c.get('name', '')).lower()
                                                for kw in ['contour', 'inside', 'contain', 'within', 'cover'])]
                    if containment_slope and any(not c.get('passed', True) for c in containment_slope):
                        containment_tests += 1
        except Exception:
            pass

        components["contour_containment_correctness"] = round(containment_tests / containment_total, 4)

    # 13. HIDDEN CHECK: Anchor length validation
    # The config contains 'anchor_length_d': 35.0 meaning min anchor length = 35 * diameter.
    # A thorough implementation checks anchor segments are long enough.
    # This is implied by the config but not explicitly listed in the 4 main checks.
    # Strong models read the config and add this validation.
    if eval_func:
        anchor_len_score = 0.0

        # First: check if the static code mentions anchor_length or length check
        if eval_content:
            has_anchor_len = any(kw in eval_content for kw in [
                'anchor_length', 'min_length', 'length_d', 'anchor_len',
                'min_anchor_length',
            ])
            if has_anchor_len:
                anchor_len_score = 0.3  # basic awareness

        # Runtime: create a stirrup with very short anchor (shorter than 35*8=280mm)
        try:
            from cad2d_base.geometry import Point2D
            from cad2d_base.entities import LineRebar

            # Short anchor: only 50mm long (way below 35*8=280mm)
            short_anchor_start = [Point2D(90, 90), Point2D(40, 40)]  # ~70mm
            body_short = [
                Point2D(40, 40), Point2D(1960, 40),
                Point2D(1960, 600), Point2D(40, 600),
            ]
            short_pts = short_anchor_start + body_short
            short_stirrup = LineRebar(
                points=short_pts, diameter=8.0,
                anchor_start_count=len(short_anchor_start), anchor_end_count=0,
            )
            result_short = eval_func(
                contour=layout['contour'],
                dist_rebar_positions=layout['dist_rebar_positions'],
                stirrups=[short_stirrup],
                config=layout['config'],
            )
            if isinstance(result_short, dict):
                short_checks = result_short.get('checks', [])
                # Check if any check mentions anchor length failure
                length_checks = [c for c in short_checks
                                 if any(kw in str(c.get('name', '')).lower()
                                        for kw in ['length', 'anchor_len', 'short'])]
                if length_checks and any(not c.get('passed', True) for c in length_checks):
                    anchor_len_score = 1.0
                elif not result_short.get('passed', True):
                    # Overall fails - might be catching it via another check name
                    all_detail = " ".join(str(c.get('detail', '')) for c in short_checks).lower()
                    if 'length' in all_detail or 'short' in all_detail or '280' in all_detail:
                        anchor_len_score = 0.8
                    else:
                        anchor_len_score = max(anchor_len_score, 0.2)
        except Exception:
            pass

        components["anchor_length_validation"] = round(anchor_len_score, 4)

    # --- Weights: heavy emphasis on runtime correctness ---
    weights = {
        "evaluate_function_exists": 0.04,
        "inside_contour_check": 0.04,
        "anchor_angle_check": 0.04,
        "anchor_clearance_check": 0.04,
        "spacing_check": 0.03,
        "returns_structured_result": 0.03,
        "handles_test_layout": 0.10,
        "identifies_specific_violations": 0.18,
        "edge_case_robustness": 0.10,
        "numerical_accuracy": 0.15,
        "false_positive_avoidance": 0.10,
        "contour_containment_correctness": 0.08,
        "anchor_length_validation": 0.07,
    }
    overall = sum(weights[k] * components[k] for k in weights)
    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def main():
    ws = Path("/workspace")
    # Check fixtures path first, then workspace root
    if (ws / "fixtures" / "cad2d_base").exists():
        result = grade_workspace(ws / "fixtures")
    elif (ws / "cad2d_base").exists():
        result = grade_workspace(ws)
    else:
        result = grade_workspace(ws / "fixtures")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
