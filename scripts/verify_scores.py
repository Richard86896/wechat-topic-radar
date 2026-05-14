#!/usr/bin/env python3
"""
评分验证脚本：检查选题报告中的七维评分加法是否正确。

用法：
    python3 scripts/verify_scores.py <选题报告.md>
    python3 scripts/verify_scores.py /path/to/vault/04.选题决策/每日选题/20260513-每日选题.md

检查项：
    1. 七维分数之和是否等于七维小计
    2. 七维小计 + 加分项 = 总分
    3. 总分对应的等级是否正确
    4. 各维度是否在满分范围内

退出码：0=全部通过 | 1=有错误 | 2=文件不存在或解析失败
"""

import re
import sys
import os

# 七维满分定义
DIMENSION_LIMITS = {
    "相关性": 20,
    "读者价值": 20,
    "判断空间": 15,
    "落地性": 15,
    "时效性": 10,
    "证据素材": 10,
    "证据与素材": 10,  # 别名
    "差异化": 10,
}

GRADE_THRESHOLDS = [
    (105, "S"),
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (0, "D"),
]


def get_grade(score):
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


def resolve_report_path(filepath):
    """Resolve report path robustly from either vault root or skill root."""
    if os.path.isabs(filepath):
        return filepath

    candidates = []
    candidates.append(os.path.abspath(filepath))

    vault_root = os.environ.get("OBSIDIAN_VAULT_ROOT", "/Users/Richard/ObsidianVaults/我的知识库")
    candidates.append(os.path.join(vault_root, filepath))

    # If called from skill root with a vault-relative path, this catches it.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(script_dir)
    candidates.append(os.path.join(skill_root, filepath))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def parse_report(filepath):
    """解析选题报告，返回每个选题的评分数据。"""
    filepath = resolve_report_path(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    topics = []

    # 按 "### 选题" 或 "## 选题" 分段
    topic_blocks = re.split(r"(?=#{2,3}\s+选题\s+\d+)", content)

    for block in topic_blocks:
        # 跳过非选题块
        title_match = re.search(r"#{2,3}\s+选题\s+\d+[：:]\s*(.+)", block)
        if not title_match:
            continue

        title = title_match.group(1).strip()
        topic_data = {
            "title": title,
            "dimensions": {},
            "bonus": 0,
            "subtotal": None,
            "total": None,
            "grade": None,
            "subtotal_formula": None,
            "total_formula": None,
        }

        # 提取七维分数 —— 支持两种格式：
        # 1. 表格格式: | 相关性 | 18/20 |
        # 2. 列表格式: - 相关性：18/20 或 - **相关性**：18/20
        for dim_name in DIMENSION_LIMITS:
            score = None
            # 尝试表格格式
            pattern_table = rf"\|\s*{re.escape(dim_name)}\s*\|\s*(\d+)\s*/\s*\d+\s*\|"
            match = re.search(pattern_table, block)
            if match:
                score = int(match.group(1))
            else:
                # 尝试列表格式（支持加粗）
                pattern_list = rf"[-*]\s*\*{{0,2}}{re.escape(dim_name)}\*{{0,2}}[：:]\s*(\d+)\s*/\s*\d+"
                match = re.search(pattern_list, block)
                if match:
                    score = int(match.group(1))
            if score is not None:
                # 统一用 "证据素材" 存储
                key = "证据素材" if dim_name == "证据与素材" else dim_name
                topic_data["dimensions"][key] = score

        # 提取七维小计算式 —— 支持多种格式：
        # 1. 代码块: 七维小计 = 18+18+... = 86
        # 2. 列表: 七维小计：86（= 18+18+...）
        # 3. 加粗+引用: > **七维小计**：86（= 18+18+...）
        subtotal_formula_match = re.search(
            r"七维小计\*{0,2}\s*[=：]\s*(\d+)\s*[（(]\s*=\s*([\d\s+]+)\s*[）)]", block
        )
        if subtotal_formula_match:
            topic_data["subtotal"] = int(subtotal_formula_match.group(1))
            topic_data["subtotal_formula"] = subtotal_formula_match.group(2).strip()
        else:
            subtotal_formula_match = re.search(
                r"七维小计\s*=\s*([\d\s+]+)\s*=\s*(\d+)", block
            )
            if subtotal_formula_match:
                topic_data["subtotal_formula"] = subtotal_formula_match.group(1).strip()
                topic_data["subtotal"] = int(subtotal_formula_match.group(2))

        # 提取总分算式 —— 支持多种格式：
        # 1. 代码块: 总分 = 七维小计(86) + 加分项(+20) = 106
        # 2. 列表: 总分/120：106（= 86 + 20）
        # 3. 加粗+引用: > **总分/120**：106（= 86 + 20）
        total_formula_match = re.search(
            r"总分\s*=\s*七维小计\((\d+)\)\s*\+\s*加分项\(\+?(\d+)\)\s*=\s*(\d+)", block
        )
        if total_formula_match:
            topic_data["total"] = int(total_formula_match.group(3))
            topic_data["total_formula"] = f"七维小计({total_formula_match.group(1)}) + 加分项(+{total_formula_match.group(2)}) = {total_formula_match.group(3)}"
        else:
            total_list_match = re.search(
                r"总分/?120\*{0,2}[：:]\s*(\d+)\s*[（(]\s*=\s*(\d+)\s*\+\s*(\d+)\s*[）)]", block
            )
            if total_list_match:
                topic_data["total"] = int(total_list_match.group(1))
                topic_data["total_formula"] = f"七维小计({total_list_match.group(2)}) + 加分项(+{total_list_match.group(3)}) = {total_list_match.group(1)}"

        # 兜底：从 "综合评分：X/120" 提取总分
        if topic_data["total"] is None:
            alt_total = re.search(r"综合评分[：:]\s*(\d+)\s*/\s*120", block)
            if alt_total:
                topic_data["total"] = int(alt_total.group(1))

        # 提取加分项 —— 支持多种格式：
        # 1. "**加分项**（命中 3 项，+12）："
        # 2. "加分项：+20（命中5项：...）"
        # 3. "加分项：+12"
        bonus_match = re.search(r"加分项\**[（(]命中\s*\d+\s*项[，,]\s*\+(\d+)[）)]", block)
        if not bonus_match:
            bonus_match = re.search(r"加分项[：:]\s*\+(\d+)[（(]命中", block)
        if bonus_match:
            topic_data["bonus"] = int(bonus_match.group(1))
        else:
            # 兜底：从总分算式中提取加分项
            if total_formula_match:
                topic_data["bonus"] = int(total_formula_match.group(2))
            else:
                alt_bonus = re.search(r"加分项[：:]\s*\+?(\d+)", block)
                if alt_bonus:
                    topic_data["bonus"] = int(alt_bonus.group(1))

        # 提取等级 —— 支持多种格式：
        # 1. 等级：S 级
        # 2. （S级）
        # 3. 表格: | S级 |
        grade_match = re.search(r"等级[：:]\s*([SABCD])\s*级", block)
        if not grade_match:
            grade_match = re.search(r"[（(]([SABCD])级[）)]", block)
        if grade_match:
            topic_data["grade"] = grade_match.group(1)

        if topic_data["dimensions"]:
            topics.append(topic_data)

    return topics


def verify_topic(topic_data, index):
    """验证单个选题的评分，返回 (errors, warnings) 列表。"""
    errors = []
    warnings = []
    dims = topic_data["dimensions"]
    title = topic_data["title"]

    # 检查是否缺失维度（核心 7 维）
    core_dims = ["相关性", "读者价值", "判断空间", "落地性", "时效性", "证据素材", "差异化"]
    missing = [d for d in core_dims if d not in dims]
    if missing:
        errors.append(f"选题{index}「{title}」: 缺失维度 {missing}")
        return errors, warnings

    # 检查维度分数范围
    for dim_name, score in dims.items():
        max_score = DIMENSION_LIMITS.get(dim_name, 20)
        if score < 0 or score > max_score:
            errors.append(f"选题{index}「{title}」: {dim_name}={score} 超出范围 [0, {max_score}]")

    # 计算七维之和
    dim_values = [dims[d] for d in core_dims]
    calc_subtotal = sum(dim_values)

    # 检查七维小计
    if topic_data["subtotal"] is not None:
        if calc_subtotal != topic_data["subtotal"]:
            errors.append(
                f"选题{index}「{title}」: 七维小计错误 "
                f"—— 实际求和={calc_subtotal}，报告写的={topic_data['subtotal']}。 "
                f"验算：{' + '.join(str(v) for v in dim_values)} = {calc_subtotal}"
            )
    else:
        warnings.append(f"选题{index}「{title}」: 报告中未写七维小计验算式")

    # 检查加分项范围
    if topic_data["bonus"] > 20:
        errors.append(f"选题{index}「{title}」: 加分项={topic_data['bonus']} 超出上限20")
    if topic_data["bonus"] > 0 and topic_data["bonus"] % 4 != 0:
        warnings.append(f"选题{index}「{title}」: 加分项={topic_data['bonus']} 不是4的倍数（每项+4）")

    # 检查总分
    expected_total = calc_subtotal + topic_data["bonus"]
    if topic_data["total"] is not None:
        if expected_total != topic_data["total"]:
            errors.append(
                f"选题{index}「{title}」: 总分错误 "
                f"—— 七维小计({calc_subtotal}) + 加分项({topic_data['bonus']}) = {expected_total}，"
                f"报告写的={topic_data['total']}"
            )
    else:
        warnings.append(f"选题{index}「{title}」: 报告中未写总分")

    # 检查等级
    if topic_data["grade"] is not None and topic_data["total"] is not None:
        expected_grade = get_grade(topic_data["total"])
        if topic_data["grade"] != expected_grade:
            errors.append(
                f"选题{index}「{title}」: 等级错误 "
                f"—— 总分{topic_data['total']}对应{expected_grade}级，报告写的={topic_data['grade']}级"
            )

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_scores.py <选题报告.md>")
        sys.exit(2)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(2)

    topics = parse_report(filepath)
    if not topics:
        print(f"⚠️ 未在文件中找到可解析的选题评分: {filepath}")
        print("   确保选题格式包含 '### 选题 N：' 和七维评分表格")
        sys.exit(2)

    all_errors = []
    all_warnings = []

    print(f"📋 验证文件: {os.path.basename(filepath)}")
    print(f"   找到 {len(topics)} 个选题")
    print("=" * 60)

    for i, topic in enumerate(topics, 1):
        errors, warnings = verify_topic(topic, i)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

        core_dims = ["相关性", "读者价值", "判断空间", "落地性", "时效性", "证据素材", "差异化"]
        dim_values = [topic["dimensions"].get(d, 0) for d in core_dims]

        if not errors and not warnings:
            dims_str = " + ".join(str(v) for v in dim_values)
            print(f"✅ 选题{i}: {topic['title'][:40]}...")
            print(f"   {dims_str} = {topic.get('subtotal', '?')} | +{topic['bonus']} → 总分 {topic.get('total', '?')} [{topic.get('grade', '?')}级]")
        else:
            print(f"选题{i}: {topic['title'][:40]}...")
            for e in errors:
                print(f"  ❌ {e}")
            for w in warnings:
                print(f"  ⚠️ {w}")

    print("=" * 60)
    print(f"📊 结果: {len(topics)} 个选题 | ❌ {len(all_errors)} 错误 | ⚠️ {len(all_warnings)} 警告")

    if all_errors:
        print("\n❌ 存在评分错误，请修正。")
        sys.exit(1)
    elif all_warnings:
        print("\n⚠️ 有警告但无硬性错误。")
        sys.exit(0)
    else:
        print("\n✅ 全部评分验证通过！")
        sys.exit(0)


if __name__ == "__main__":
    main()
