#!/usr/bin/env python3
"""
文章事实核查脚本
自动检查文章中的事实准确性

用法:
  python3 fact_checker.py articles/20260421-库克卸任苹果CEO.md
  python3 fact_checker.py --check-all topics/
"""

import argparse
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

# 尝试读取配置文件
REFERENCES_DIR = Path(__file__).parent.parent / "references"


def load_fact_database() -> Dict:
    """加载事实数据库（已废弃，保留接口兼容）"""
    # 实时校验不再依赖静态数据库，统一使用 WebSearch 验证
    return {}


def load_language_rules() -> Dict:
    """加载语言安全规则"""
    rules_file = REFERENCES_DIR / "language_safety.md"
    if not rules_file.exists():
        return {"forbidden": [], "uncertainty_needed": [], "data_limits": []}

    content = rules_file.read_text()

    # 提取禁用词
    forbidden = []
    # 提取需要加限定词的表述
    uncertainty_needed = []

    # 简化解析
    patterns = {
        "forbidden": [
            r"内部消息",
            r"据知情人士",
            r"必然|注定|一定会",
            r"彻底失败|全面落后",
        ],
        "uncertainty": [
            (r"选择在.*?卸任", "选择...卸任"),
            (r"显然已经落后", "相对落后"),
            (r"将推出", "可能推出"),
            (r"将彻底改变", "可能深刻影响"),
            (r"必将", "有望"),
        ]
    }

    return patterns


def check_facts(content: str) -> List[Dict]:
    """检查文章中的事实"""
    issues = []

    # 1. 检查年龄相关
    if "65岁" in content or "年近70" in content or "60多岁" in content:
        issues.append({
            "type": "fact",
            "severity": "warning",
            "line": "age",
            "issue": "库克出生于1960年1月24日，2026年为66岁",
            "suggestion": "改为'66岁'或'65岁'（取决于精确度）"
        })

    # 2. 检查苹果历史
    if "34年历史" in content:
        issues.append({
            "type": "fact",
            "severity": "error",
            "line": "apple_history",
            "issue": "苹果成立于1976年，2026年应为50周年",
            "suggestion": "改为'50年历史'或'2026年迎来50周年'"
        })

    # 3. 检查市值数据（需要加约等词）
    precise_numbers = re.findall(r'\$[4-5]\.\d{2}万亿', content)
    if precise_numbers and "约" not in content and "接近" not in content:
        issues.append({
            "type": "fact",
            "severity": "warning",
            "line": "market_cap",
            "issue": f"发现精确市值数据: {precise_numbers}",
            "suggestion": "市值数据应加'约'、'接近'等限定词"
        })

    return issues


def check_language_safety(content: str) -> List[Dict]:
    """检查语言安全性"""
    issues = []

    # 禁用词汇
    forbidden_patterns = [
        (r"内部消息", "使用匿名信息源"),
        (r"据知情人士透露", "使用匿名信息源"),
        (r"必然", "过度确定性表述"),
        (r"注定", "过度确定性表述"),
        (r"必将", "过度确定性表述"),
        (r"彻底失败", "过度负面表述"),
        (r"全面落后", "过度负面表述"),
    ]

    for pattern, desc in forbidden_patterns:
        if re.search(pattern, content):
            issues.append({
                "type": "language",
                "severity": "error",
                "pattern": pattern,
                "issue": f"发现禁用表述: {desc}",
                "suggestion": "移除或替换为中性表述"
            })

    # 需要加限定词的表述
    uncertainty_patterns = [
        (r"(?<!可能)库克选择在.*?卸任", "原因推断过于确定"),
        (r"(?<!相对)明显落后(?!于)", "主观判断"),
        (r"苹果将推出(?!可能)", "未来预测过于确定"),
        (r"(?<!可能)将彻底改变", "过度宏大预测"),
    ]

    for pattern, desc in uncertainty_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            issues.append({
                "type": "language",
                "severity": "warning",
                "match": match.group(),
                "issue": f"表述{desc}",
                "suggestion": "添加'可能'、'或许'等限定词"
            })

    # 时间准确性检查
    if "库克已退休" in content:
        issues.append({
            "type": "time",
            "severity": "error",
            "issue": "库克尚未退休（仅宣布将于9月卸任）",
            "suggestion": "改为'库克宣布将于9月退休'"
        })

    if re.search(r"库克最近宣布", content):
        issues.append({
            "type": "time",
            "severity": "warning",
            "issue": "应使用具体日期而非'最近'",
            "suggestion": "改为'库克于2026年4月宣布'"
        })

    return issues


def check_data_annotations(content: str) -> List[Dict]:
    """检查数据来源标注"""
    issues = []

    # 检查是否引用了财务数据但没有标注
    has_numbers = bool(re.search(r'\$[\d,]+亿', content))
    has_annotations = "公开财报" in content or "公开报道" in content or "来源" in content

    if has_numbers and not has_annotations:
        issues.append({
            "type": "data",
            "severity": "warning",
            "issue": "发现财务数据但缺少来源标注",
            "suggestion": "添加数据来源说明，如'（数据来源：苹果公开财报）'"
        })

    return issues


def check_comparison_neutrality(content: str) -> List[Dict]:
    """检查对比表述的中立性"""
    issues = []

    # 检查是否过度贬低某公司
    negative_patterns = [
        (r"明显落后", "苹果在AI领域相对谨慎，而非明显落后"),
        (r"全面落后", "避免使用全面落后等绝对化表述"),
    ]

    for pattern, suggestion in negative_patterns:
        if re.search(pattern, content):
            issues.append({
                "type": "neutrality",
                "severity": "warning",
                "issue": f"对比表述可能不够中立",
                "suggestion": suggestion
            })

    return issues


def analyze_article(file_path: str) -> Dict:
    """分析单篇文章"""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"文件不存在: {file_path}"}

    content = path.read_text()

    all_issues = []
    all_issues.extend(check_facts(content))
    all_issues.extend(check_language_safety(content))
    all_issues.extend(check_data_annotations(content))
    all_issues.extend(check_comparison_neutrality(content))

    # 统计
    error_count = sum(1 for i in all_issues if i["severity"] == "error")
    warning_count = sum(1 for i in all_issues if i["severity"] == "warning")

    return {
        "file": str(path),
        "total_issues": len(all_issues),
        "errors": error_count,
        "warnings": warning_count,
        "issues": all_issues,
        "status": "PASS" if error_count == 0 else "FAIL"
    }


def print_report(result: Dict):
    """打印检查报告"""
    print("=" * 60)
    print(f"文件: {result.get('file', 'N/A')}")
    print("=" * 60)

    if "error" in result:
        print(f"❌ {result['error']}")
        return

    print(f"\n📊 检查结果: {result['status']}")
    print(f"   错误: {result['errors']} | 警告: {result['warnings']}")

    if result["issues"]:
        print("\n📋 问题列表:")
        for i, issue in enumerate(result["issues"], 1):
            severity_icon = "❌" if issue["severity"] == "error" else "⚠️"
            print(f"\n{severity_icon} [{issue['type']}] {issue['issue']}")
            print(f"   建议: {issue['suggestion']}")
    else:
        print("\n✅ 未发现问题")

    print()


def main():
    parser = argparse.ArgumentParser(description="文章事实核查工具")
    parser.add_argument("file", nargs="?", help="要检查的文章文件")
    parser.add_argument("--check-all", dest="check_all", help="检查目录下所有md文件")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")

    args = parser.parse_args()

    files_to_check = []

    if args.file:
        files_to_check = [args.file]
    elif args.check_all:
        dir_path = Path(args.check_all)
        files_to_check = list(dir_path.glob("*.md"))
    else:
        print("请指定要检查的文件或目录")
        print("用法: python3 fact_checker.py article.md")
        print("     python3 fact_checker.py --check-all topics/")
        return

    results = []
    for file in files_to_check:
        result = analyze_article(str(file))
        results.append(result)
        if args.format == "text":
            print_report(result)

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))

    # 汇总
    total_errors = sum(r.get("errors", 0) for r in results)
    total_warnings = sum(r.get("warnings", 0) for r in results)

    print("\n" + "=" * 60)
    print("📊 汇总:")
    print(f"   检查文件: {len(files_to_check)}")
    print(f"   总错误: {total_errors} | 总警告: {total_warnings}")

    if total_errors == 0:
        print("\n✅ 全部检查通过!")
    else:
        print("\n❌ 存在错误，请修正后重试")


if __name__ == "__main__":
    main()
