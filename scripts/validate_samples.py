#!/usr/bin/env python3
# ============================================================
# 智能知识库平台 - 样本验证脚本
# 用途：遍历 manifest.json 中的所有样本，验证文件完整性
# 用法：uv run python scripts/validate_samples.py
# 退出码：0 = 全部通过, 1 = 存在不通过的样本
# ============================================================

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


# 项目根目录（脚本所在目录的上级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SAMPLE_ROOT = PROJECT_ROOT / "samples"
DOCUMENT_ROOT = SAMPLE_ROOT / "documents"
SUPPORT_FILE_ALLOWLIST = {"documents/images/normal/ground-truth.json"}


def load_manifest():
    """加载样本清单文件"""
    manifest_path = PROJECT_ROOT / "samples" / "manifest.json"
    if not manifest_path.exists():
        print(f"[错误] 样本清单文件不存在: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_sha256(file_path: Path) -> str:
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_missing_markdown_resources(file_path: Path) -> list[str]:
    """返回 Markdown 中不存在的本地资源；外部 URL 和页内锚点不在此校验。"""
    missing: list[str] = []
    content = file_path.read_text(encoding="utf-8")
    for raw_target in MARKDOWN_LINK_PATTERN.findall(content):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if not target or target.startswith(("#", "http://", "https://", "data:")):
            continue
        resource_path = (file_path.parent / target.split("#", maxsplit=1)[0]).resolve()
        if not resource_path.is_file():
            missing.append(target)
    return missing


def validate_sample(sample: dict) -> dict:
    """
    验证单个样本
    返回验证结果字典
    """
    sample_id = sample["id"]
    sample_path = (SAMPLE_ROOT / sample["path"]).resolve()
    results = {
        "id": sample_id,
        "path": sample["path"],
        "format": sample["format"],
        "category": sample["category"],
        "exists": False,
        "size_match": None,
        "sha256_match": None,
        "errors": [],
    }

    if not sample_path.is_relative_to(SAMPLE_ROOT.resolve()):
        results["errors"].append("样本路径越出 samples 目录")
        return results

    # 对于 status 为 pending 的样本，跳过所有检查
    if sample.get("status") == "pending":
        results["exists"] = "skipped"
        results["size_match"] = "skipped"
        results["sha256_match"] = "skipped"
        return results

    # 检查文件是否存在
    if not sample_path.exists():
        results["errors"].append(f"文件不存在: {sample_path}")
        return results

    results["exists"] = True
    actual_size = sample_path.stat().st_size

    # 检查文件大小
    expected_size = sample.get("file_size_bytes")
    if isinstance(expected_size, int) and expected_size >= 0:
        if actual_size != expected_size:
            results["size_match"] = False
            results["errors"].append(
                f"文件大小不匹配: 期望 {expected_size} 字节, 实际 {actual_size} 字节"
            )
        else:
            results["size_match"] = True
    else:
        results["errors"].append("manifest 未记录 file_size_bytes")

    # 检查 SHA256
    expected_sha256 = sample.get("sha256", "")
    if expected_sha256:
        actual_sha256 = compute_sha256(sample_path)
        if actual_sha256 != expected_sha256:
            results["sha256_match"] = False
            results["errors"].append(
                f"SHA256 不匹配: 期望 {expected_sha256[:16]}..., 实际 {actual_sha256[:16]}..."
            )
        else:
            results["sha256_match"] = True
    else:
        results["errors"].append("manifest 未记录 sha256")

    if sample["format"] in {"md", "markdown"}:
        for target in find_missing_markdown_resources(sample_path):
            results["errors"].append(f"Markdown 本地资源不存在: {target}")

    return results


def main():
    """主流程"""
    print("=" * 60)
    print("  智能知识库平台 - 样本验证")
    print("=" * 60)
    print()

    # 加载样本清单
    manifest = load_manifest()
    samples = manifest.get("samples", [])
    print(f"样本总数: {len(samples)}")
    print()

    ids = [sample.get("id") for sample in samples]
    paths = [sample.get("path") for sample in samples]
    manifest_errors = [
        f"重复样本 ID: {value}"
        for value, count in Counter(ids).items()
        if count > 1
    ]
    manifest_errors.extend(
        f"重复样本路径: {value}"
        for value, count in Counter(paths).items()
        if count > 1
    )
    registered_paths = {path for path in paths if isinstance(path, str)}
    actual_paths = {
        file.relative_to(SAMPLE_ROOT).as_posix()
        for file in DOCUMENT_ROOT.rglob("*")
        if file.is_file()
    }
    manifest_errors.extend(
        f"未登记样本文件: {path}"
        for path in sorted(actual_paths - registered_paths - SUPPORT_FILE_ALLOWLIST)
    )

    # 验证每个样本
    passed = 0
    failed = 0
    pending = 0
    errors = []

    for sample in samples:
        result = validate_sample(sample)

        if result["errors"]:
            failed += 1
            status = "失败"
            errors.append(result)
        elif result["exists"] == "skipped":
            pending += 1
            status = "待制作"
        else:
            passed += 1
            status = "通过"

        print(f"  [{status}] {result['id']}: {result['path']}")

    # 输出汇总
    print()
    print("=" * 60)
    print(f"  验证结果: {passed} 通过, {failed} 失败, {pending} 待制作")

    if errors:
        print()
        print("  失败详情:")
        for err in errors:
            print(f"    - {err['id']}: {err['path']}")
            for e in err["errors"]:
                print(f"      {e}")
    if manifest_errors:
        print()
        print("  清单结构失败:")
        for error in manifest_errors:
            print(f"    - {error}")

    print("=" * 60)

    # 退出码：存在失败则返回 1
    if failed > 0 or manifest_errors:
        print()
        print("注意: 二进制样本（PDF/DOCX/XLSX/PPTX/EPUB/图片）需要手动制作。")
        print("请参考 samples/README.md 中的说明。")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
