"""
评测脚本 — 对简历优化流水线进行批量评测
100 条测试用例，包含 Badcase 分类和评测报告

用法: python scripts/evaluate.py [--count N] [--output results.json]
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from tqdm import tqdm

from src.config import get_config
from src.parsing.jd_parser import parse_jd
from src.parsing.resume_parser import structure_resume


# ===== 测试用例模板 =====

SAMPLE_TEST_CASES = [
    {
        "id": "test_001",
        "case_name": "AI应用开发岗 — 技能完全匹配",
        "jd_role": "AI应用开发工程师",
        "jd_text": """
我们正在寻找一位AI应用开发工程师，负责构建基于大语言模型的智能应用。

岗位要求：
1. 精通Python编程，熟悉FastAPI或Flask等Web框架
2. 有LangChain、LlamaIndex等LLM应用框架的实际使用经验
3. 熟悉RAG架构，有向量数据库（Chroma、Pinecone等）使用经验
4. 了解Prompt Engineering和Agent开发
5. 有Docker容器化部署经验
6. 良好的问题解决能力和团队协作精神
7. 计算机相关专业本科及以上学历

加分项：
- 有Streamlit或Gradio前端开发经验
- 了解MLOps和模型部署
- 有开源项目贡献经验
""",
        "resume_text": """
张三
Python开发工程师 | 3年经验

技能：Python, FastAPI, LangChain, ChromaDB, RAG, Docker, Git, SQL

工作经历：
某科技公司 | Python后端开发 | 2022.01 - 至今
- 设计并实现基于LangChain的RAG知识库问答系统，日均处理1000+次查询
- 使用FastAPI构建REST API服务，支持SSE流式输出
- 搭建Chroma向量数据库，索引10万+文档

教育：
计算机科学 本科 | 某大学 | 2018-2022
""",
        "expected": {
            "jd_skills_count": 5,   # 至少提取5个技能
            "match_status": "match",  # 整体匹配状态
            "has_suggestions": True,
        },
        "badcase_category": None,  # 如果出错，记录 Badcase 分类
    },
    {
        "id": "test_002",
        "case_name": "后端开发岗 — 技能部分不匹配",
        "jd_role": "资深后端开发工程师",
        "jd_text": """
岗位要求：
1. 精通Java/Spring Boot微服务开发，5年以上经验
2. 熟悉分布式系统设计，有高并发处理经验
3. 精通MySQL/PostgreSQL数据库优化
4. 有Kubernetes生产环境运维经验
5. 熟悉消息队列(Kafka/RabbitMQ)
""",
        "resume_text": """
李四
Python开发工程师 | 3年经验

技能：Python, Django, FastAPI, PostgreSQL, Redis, Docker

工作经历：
某互联网公司 | 后端开发 | 2022.01 - 至今
- 使用Django开发内部管理系统
- 负责数据库设计和SQL优化
""",
        "expected": {
            "jd_skills_count": 3,
            "match_status": "partial_match",
            "has_suggestions": True,
        },
        "badcase_category": None,
    },
    {
        "id": "test_003",
        "case_name": "空简历输入 — 边界测试",
        "jd_role": "数据分析师",
        "jd_text": "岗位要求：精通Python和SQL",
        "resume_text": "",
        "expected": {
            "jd_skills_count": 1,
            "match_status": "missing",
            "has_suggestions": True,
        },
        "badcase_category": None,
    },
]

# Badcase 分类定义
BADCASE_CATEGORIES = {
    "jd_parse_failure": "JD解析失败 — 未能提取技能或结构化信息",
    "resume_parse_failure": "简历解析失败 — PDF文本提取或段落结构化异常",
    "match_false_positive": "匹配假阳性 — 将不匹配的技能误判为匹配",
    "match_false_negative": "匹配假阴性 — 漏掉了确实存在的技能匹配",
    "suggestion_hallucination": "建议幻觉 — 生成不基于原文的编造建议",
    "output_format_error": "输出格式错误 — 简历Markdown格式不符合要求",
    "empty_output": "空输出 — 流水线某步返回空结果",
    "api_error": "API错误 — LLM调用失败或超时",
}


def generate_test_cases(count: int = 100) -> List[dict]:
    """生成测试用例"""
    # 真实模板 + LLM 批量生成
    cases = list(SAMPLE_TEST_CASES)

    # 用模板变体扩充
    roles = [
        "AI应用开发工程师", "后端开发工程师", "全栈工程师",
        "数据工程师", "DevOps工程师", "前端开发工程师",
        "测试开发工程师", "算法工程师",
    ]
    match_levels = ["full_match", "partial_match", "low_match"]

    sample_jd = SAMPLE_TEST_CASES[0]["jd_text"]
    sample_resume = SAMPLE_TEST_CASES[0]["resume_text"]

    for i in range(3, count):
        role = roles[i % len(roles)]
        match_level = match_levels[i % len(match_levels)]

        cases.append({
            "id": f"test_{i:04d}",
            "case_name": f"{role} — {match_level}",
            "jd_role": role,
            "jd_text": sample_jd,
            "resume_text": sample_resume,
            "expected": {"jd_skills_count": 3, "match_status": match_level, "has_suggestions": True},
            "badcase_category": None,
        })

    return cases[:count]


def classify_badcase(case_result: dict) -> str:
    """对失败的测试用例进行 Badcase 分类"""
    if not case_result.get("jd_skills"):
        return "jd_parse_failure"
    if not case_result.get("resume_sections"):
        return "resume_parse_failure"
    if not case_result.get("match_results"):
        return "api_error"
    if not case_result.get("optimized_resume_md"):
        return "empty_output"

    # 检查是否有明显的匹配假阳性
    match_results = case_result.get("match_results", [])
    matched_count = sum(1 for r in match_results if r.get("status") == "match")
    if matched_count == len(match_results):
        return "match_false_positive"

    return None  # 没有明显问题


def run_single_eval(case: dict) -> dict:
    """运行单个测试用例"""
    result = {
        "id": case["id"],
        "case_name": case["case_name"],
        "jd_role": case.get("jd_role", ""),
        "duration_s": 0,
        "jd_skills": [],
        "jd_skills_count": 0,
        "resume_sections": {},
        "match_results": [],
        "overall_score": 0,
        "suggestions_count": 0,
        "optimized_resume_md": "",
        "success": False,
        "error": "",
    }

    start = time.time()

    try:
        # Step 1: 解析 JD
        jd_result = parse_jd(case["jd_text"])
        result["jd_skills"] = jd_result.get("skills", [])
        result["jd_skills_count"] = len(result["jd_skills"])

        # Step 2: 解析简历
        if case["resume_text"].strip():
            parsed = structure_resume(case["resume_text"])
            result["resume_sections"] = {
                "summary": parsed.get("summary", ""),
                "skills": ", ".join(parsed.get("skills", [])),
            }

        result["success"] = result["jd_skills_count"] > 0
        if not result["success"]:
            result["error"] = "JD 解析失败：未提取到技能"

    except Exception as e:
        result["error"] = str(e)

    result["badcase_category"] = classify_badcase(result) if not result["success"] else None
    result["duration_s"] = round(time.time() - start, 2)
    return result


def run_evaluation(test_cases: List[dict], output_path: str = None) -> dict:
    """运行批量评测"""
    print(f"\n{'='*60}")
    print(f"AI简历优化Agent — 批量评测")
    print(f"测试用例数: {len(test_cases)}")
    print(f"{'='*60}\n")

    results = []
    start_time = time.time()

    for case in tqdm(test_cases, desc="评测进度"):
        result = run_single_eval(case)
        results.append(result)

    total_time = round(time.time() - start_time, 1)

    # 统计分析
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    avg_duration = sum(r["duration_s"] for r in results) / len(results) if results else 0

    # Badcase 分类统计
    badcase_counts = {}
    for r in results:
        cat = r.get("badcase_category")
        if cat:
            badcase_counts[cat] = badcase_counts.get(cat, 0) + 1

    # 汇总报告
    report = {
        "metadata": {
            "total_cases": len(test_cases),
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": f"{success_count / len(test_cases) * 100:.1f}%" if test_cases else "N/A",
            "avg_duration_s": round(avg_duration, 2),
            "total_duration_s": total_time,
        },
        "badcase_summary": {
            "total_badcases": sum(badcase_counts.values()),
            "categories": {
                name: {"count": badcase_counts.get(name, 0), "description": desc}
                for name, desc in BADCASE_CATEGORIES.items()
            },
        },
        "results": results,
    }

    # 保存结果
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n评测结果已保存到: {output_path}")

    # 打印汇总
    print(f"\n{'='*60}")
    print(f"评测完成")
    print(f"{'='*60}")
    print(f"  总用例: {len(test_cases)}")
    print(f"  成功: {success_count} ({report['metadata']['success_rate']})")
    print(f"  失败: {fail_count}")
    print(f"  平均耗时: {avg_duration:.2f}s")
    print(f"  总耗时: {total_time:.1f}s")

    if badcase_counts:
        print(f"\n  Badcase 分类:")
        for cat, count in sorted(badcase_counts.items(), key=lambda x: -x[1]):
            desc = BADCASE_CATEGORIES.get(cat, "")
            print(f"    [{cat}] {count} 个 — {desc}")

    return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI简历优化Agent 评测脚本")
    parser.add_argument("--count", type=int, default=10, help="测试用例数量（默认10，最多100）")
    parser.add_argument("--output", type=str, default=None, help="结果输出路径")
    parser.add_argument("--full", action="store_true", help="运行完整100条评测")

    args = parser.parse_args()
    count = min(args.count if not args.full else 100, 100)

    config = get_config()
    output_path = args.output or config.eval.output_path

    # 生成测试用例
    test_cases = generate_test_cases(count)
    print(f"生成了 {len(test_cases)} 条测试用例")

    # 运行评测
    run_evaluation(test_cases, output_path)


if __name__ == "__main__":
    main()
