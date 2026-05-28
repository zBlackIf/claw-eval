"""Hidden verifier for CP99 — OSS Storage Factory Pattern."""
from __future__ import annotations

import json
from pathlib import Path


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def grade_workspace(ws: Path) -> dict:
    oss = ws / "datares-warehouse" / "src" / "main" / "java" / "cn" / "dtdream" / "datares" / "warehouse" / "store" / "oss"
    components = {k: 0.0 for k in [
        "interface_created", "abstract_base_created", "minio_updated",
        "factory_created", "service_facade_created", "no_extra_vendors",
        "uses_aws_sdk",
    ]}

    interface_file = next((p for p in oss.rglob("OssClient.java")), None) if oss.exists() else None
    if interface_file and interface_file.exists():
        c = _read(interface_file)
        has_iface = "interface" in c
        has_upload = "put" in c.lower() or "upload" in c.lower()
        has_download = "get" in c.lower() or "download" in c.lower()
        has_delete = "delete" in c.lower()
        components["interface_created"] = min(1.0, (0.4 if has_iface else 0.0) + sum([has_upload, has_download, has_delete]) * 0.2)

    abs_file = next((p for p in oss.rglob("Abstract*OssClient.java")), None) if oss.exists() else None
    if abs_file and abs_file.exists():
        c = _read(abs_file)
        has_abstract = "abstract" in c
        has_s3 = "S3Client" in c or "s3Client" in c
        components["abstract_base_created"] = 1.0 if (has_abstract and has_s3) else (0.5 if has_abstract else 0.0)

    minio_file = next((p for p in oss.rglob("Minio*Client.java")), None) if oss.exists() else None
    if minio_file and minio_file.exists():
        c = _read(minio_file)
        components["minio_updated"] = 1.0 if ("extends" in c and "Abstract" in c) else 0.5

    factory_file = next((p for p in oss.rglob("*Factory*.java")), None) if oss.exists() else None
    components["factory_created"] = 1.0 if factory_file and factory_file.exists() else 0.0

    svc_file = None
    if (ws / "datares-warehouse").exists():
        for p in (ws / "datares-warehouse").rglob("*OssStorage*Service*.java"):
            svc_file = p
            break
        if not svc_file:
            for p in (ws / "datares-warehouse").rglob("*Oss*Service*.java"):
                svc_file = p
                break
    components["service_facade_created"] = 1.0 if svc_file and svc_file.exists() else 0.0

    extra = []
    for v in ["aliyun", "tencent", "aws"]:
        d = oss / v
        if d.exists() and d.is_dir():
            extra.append(v)
    components["no_extra_vendors"] = 1.0 if not extra else (0.5 if len(extra) == 1 else 0.0)

    aws_found = False
    if oss.exists():
        for jf in oss.rglob("*.java"):
            c = _read(jf)
            if "software.amazon.awssdk" in c or "S3Client" in c:
                aws_found = True
                break
    components["uses_aws_sdk"] = 1.0 if aws_found else 0.0

    weights = {
        "interface_created": 0.20,
        "abstract_base_created": 0.20,
        "minio_updated": 0.15,
        "factory_created": 0.15,
        "service_facade_created": 0.10,
        "no_extra_vendors": 0.10,
        "uses_aws_sdk": 0.10,
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
