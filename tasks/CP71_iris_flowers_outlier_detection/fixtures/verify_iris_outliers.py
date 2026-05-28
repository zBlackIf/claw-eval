"""Hidden verifier for CP71 — Iris flowers outlier detection."""
from __future__ import annotations

import json
import re
from pathlib import Path


REPORT_NAMES = ["iris_outliers.md", "outliers.md", "report.md",
                "iris_report.md", "outlier_analysis.md", "iris_outlier_report.md"]


def _find(ws: Path) -> Path | None:
    for n in REPORT_NAMES:
        p = ws / n
        if p.exists():
            return p
    return None


def grade_workspace(ws: Path) -> dict:
    report = _find(ws)
    components = {k: 0.0 for k in [
        "report_created", "method_explained", "feature_outliers",
        "sample_evidence", "within_species", "unusual_observations", "summary",
    ]}
    if not report:
        return {"overall_score": 0.0, "components": components}

    content = report.read_text(encoding="utf-8", errors="ignore")
    lower = content.lower()
    components["report_created"] = 1.0

    # Method explanation: ≥2 patterns
    method_pats = [
        r"iqr|inter\s*-?\s*quartile\s*range",
        r"z\s*-?\s*score",
        r"robust\s+z|mad|median\s+absolute\s+deviation",
        r"mahalanobis|isolation\s*forest|local\s*outlier|multivariate",
        r"(?:1\.5|1\.5\s*[*×x]\s*iqr)",
        r"(?:standard\s*deviation|sigma).*(?:outlier|threshold)",
        r"(?:upper|lower)\s*(?:fence|bound|whisker)",
        r"(?:per|by|within|each)[- ](?:species|class|group)",
    ]
    m_count = sum(1 for p in method_pats if re.search(p, lower))
    components["method_explained"] = 1.0 if m_count >= 2 else (0.5 if m_count >= 1 else 0.0)

    # Outlier feature(s) identified. SepalWidth is the classic global IQR
    # finding, but species-level and multivariate analyses may reasonably
    # foreground other measurements.
    feature_pats = [
        r"sepal\s*width.*(?:outlier|anomal|extreme)|(?:outlier|anomal|extreme).*sepal\s*width",
        r"sepalwidth.*(?:outlier|anomal|extreme)|(?:outlier|anomal|extreme).*sepalwidth",
        r"sepal\s*length.*(?:outlier|anomal|extreme)|(?:outlier|anomal|extreme).*sepal\s*length",
        r"petal\s*(?:length|width).*(?:outlier|anomal|extreme)|(?:outlier|anomal|extreme).*petal\s*(?:length|width)",
        r"(?:setosa|versicolor|virginica).*(?:outlier|anomal|extreme)",
    ]
    f_count = sum(1 for p in feature_pats if re.search(p, lower))
    components["feature_outliers"] = 1.0 if f_count >= 2 else (0.5 if f_count >= 1 else 0.0)

    # Sample evidence: values + row/index references. Accept common row
    # conventions: record index, CSV line including header, and 0-based index.
    evidence = 0.0
    value_hits = sum(1 for p in [r"4\.4", r"4\.1", r"4\.2", r"\b2\.0\b", r"\b2\.3\b", r"\b4\.9\b"] if re.search(p, content))
    evidence += min(value_hits / 4.0, 1.0) * 0.55
    row_variants = [
        "15", "16", "17", "32", "33", "34", "35", "41", "42", "43",
        "60", "61", "62", "106", "107", "108",
    ]
    row_pat = rf"(?:row|sample|observation|index|record|line|第)\s*(?:#?\s*)?(?:{'|'.join(row_variants)})"
    if re.search(row_pat, lower):
        evidence += 0.30
    if re.search(r"sepal\s*width|sepalwidth|sepal\s*length|petal\s*(?:length|width)", lower):
        evidence += 0.15
    components["sample_evidence"] = min(evidence, 1.0)

    # Within-species
    within_pats = [
        r"within[- ]species.*outlier",
        r"(?:per|each|by)[- ]species.*outlier",
        r"outlier.*(?:within|per|each|by)[- ](?:species|group|class)",
        r"(?:setosa|versicolor|virginica).*(?:outlier|extreme|unusual).*(?:within|for\s+(?:its|the)\s+species)",
        r"(?:group|species|class)[- ](?:level|specific|wise).*outlier",
        r"分(?:品种|物种|类别|组).*异常|按(?:品种|物种|类别|组).*异常",
    ]
    components["within_species"] = 1.0 if any(re.search(p, lower) for p in within_pats) else 0.0

    # Unusual observations
    un_pats = [
        r"(?:unusual|atypical|anomal).*(?:observ|sample|row|specimen)",
        r"(?:row|sample)\s*(?:#?\s*)?(?:42|107).*(?:unusual|atypical|extreme|outlier)",
        r"(?:virginica|setosa).*(?:small|low|unusual|atypical)",
        r"sepal\s*width\s*(?:=|of|:)?\s*2\.3.*setosa",
        r"sepal\s*length\s*(?:=|of|:)?\s*4\.9.*virginica",
        r"(?:multi[- ]?feature|multivariate|多(?:特征|变量))",
        r"(?:mislabel|misclassif|wrong\s*(?:label|species))",
    ]
    un_count = sum(1 for p in un_pats if re.search(p, lower))
    components["unusual_observations"] = 1.0 if un_count >= 2 else (0.5 if un_count >= 1 else 0.0)

    # Summary
    sum_pats = [
        r"(?:total|found)\s*\d+\s*outlier",
        r"\d+\s*outlier.*(?:found|detected|identified)",
        r"(?:summary|conclusion|overall)",
        r"(?:most|primarily).*(?:sepal\s*width|affected|feature|species)",
        r"总结|结论|整体来看",
    ]
    s_count = sum(1 for p in sum_pats if re.search(p, lower))
    components["summary"] = 1.0 if s_count >= 2 else (0.5 if s_count >= 1 else 0.0)

    weights = {
        "report_created": 0.05,
        "method_explained": 0.15,
        "feature_outliers": 0.15,
        "sample_evidence": 0.20,
        "within_species": 0.15,
        "unusual_observations": 0.15,
        "summary": 0.15,
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
