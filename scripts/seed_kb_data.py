"""
知识库种子数据生成器 — 使用 LLM 扩充知识库数据
用法: python scripts/seed_kb_data.py [--expand]
  --expand: 使用 LLM 扩充数据（需要 DeepSeek API Key）
  不加参数: 检查现有数据完整性
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generation.llm import get_llm


def check_data():
    """检查知识库数据完整性"""
    kb_dir = Path(__file__).parent.parent / "data" / "kb"
    files = {
        "skill_taxonomy.json": "技能分类",
        "resume_best_practices.json": "简历最佳实践",
        "ats_keywords.json": "ATS关键词",
    }

    print("=" * 50)
    print("知识库数据完整性检查")
    print("=" * 50)

    all_ok = True
    for filename, name in files.items():
        path = kb_dir / filename
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                print(f"  {name}: {len(data)} 条记录")
            else:
                print(f"  {name}: 存在（非列表格式）")
        else:
            print(f"  {name}: 缺失!")
            all_ok = False

    if all_ok:
        print("\n所有数据文件完整。运行 python scripts/build_kb.py 构建索引。")
    else:
        print("\n部分数据文件缺失，运行 python scripts/seed_kb_data.py --expand 扩充数据。")


def expand_with_llm():
    """使用 LLM 扩充数据（示例：为更多岗位添加技能分类）"""
    print("=" * 50)
    print("使用 LLM 扩充知识库数据")
    print("=" * 50)

    llm = get_llm(temperature=0.3)
    kb_dir = Path(__file__).parent.parent / "data" / "kb"

    # 读取现有数据
    path = kb_dir / "skill_taxonomy.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    existing_roles = {e.get("role", "") for e in existing}

    # 扩充更多岗位
    additional_roles = [
        "DevOps/SRE Engineer",
        "Security Engineer",
        "QA/Test Engineer",
        "Product Manager (Technical)",
    ]

    new_roles = [r for r in additional_roles if r not in existing_roles]
    if not new_roles:
        print("所有岗位已有数据，无需扩充。")
        return

    for role in new_roles:
        print(f"\n生成岗位: {role}")
        prompt = f"""你是一位资深技术招聘专家。请为「{role}」岗位生成技能分类数据。

格式要求：返回一个 JSON 对象，包含技能的 name（技能名）、category（hard/soft/tool）、description（中文描述，50-100字）、ats_keywords（5-10个ATS关键词）。

请生成 6-8 个核心技能，覆盖硬技能、工具和软技能。
只返回 JSON 数组，不要其他文字。"""

        try:
            from langchain_core.messages import HumanMessage
            response = llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # 提取 JSON
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            skills = json.loads(content)
            existing.append({
                "role": role,
                "skills": skills if isinstance(skills, list) else skills.get("skills", []),
            })
            print(f"  生成了 {len(existing[-1]['skills'])} 个技能")
        except Exception as e:
            print(f"  生成失败: {e}")

    # 保存
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n数据已保存至: {path}")
    print(f"总计 {len(existing)} 个岗位")


def main():
    if "--expand" in sys.argv:
        expand_with_llm()
    else:
        check_data()
        print("\n提示: 使用 --expand 参数可调用 LLM 扩充数据")


if __name__ == "__main__":
    main()
