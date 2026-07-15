"""
构建知识库 — 从 JSON 源数据生成 Chroma 索引
用法: python scripts/build_kb.py [--force]
  --force: 强制重建（清空已有索引）
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.indexer import get_index_builder
from src.config import get_config


def load_json(path: str) -> list:
    """加载 JSON 文件"""
    if not os.path.exists(path):
        print(f"  文件不存在: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_skill_taxonomy(builder, force: bool):
    """
    构建技能分类知识库
    将每个角色的技能描述作为独立文档索引
    """
    config = get_config()
    collection_name = config.knowledge_base.collection_skill_taxonomy
    data_path = os.path.join(config.knowledge_base.data_dir, "skill_taxonomy.json")

    if force:
        builder.clear_collection(collection_name)

    data = load_json(data_path)
    if not data:
        print("  无数据，跳过")
        return

    documents = []
    metadatas = []

    for role_entry in data:
        role = role_entry.get("role", "")
        for skill in role_entry.get("skills", []):
            # 构建文档内容：技能名 + 描述 + ATS关键词
            content_parts = [
                f"技能: {skill['name']}",
                f"类别: {skill['category']}",
                f"适用岗位: {role}",
                f"描述: {skill['description']}",
                f"ATS关键词: {', '.join(skill.get('ats_keywords', []))}",
            ]
            documents.append("\n".join(content_parts))
            metadatas.append({
                "skill_name": skill["name"],
                "category": skill["category"],
                "role": role,
                "ats_keywords": ",".join(skill.get("ats_keywords", [])),
            })

    count = builder.index_documents(collection_name, documents, metadatas)
    print(f"  [{collection_name}] 索引完成: {count} 条技能")


def build_best_practices(builder, force: bool):
    """
    构建简历最佳实践知识库
    每条实践作为一个独立文档
    """
    config = get_config()
    collection_name = config.knowledge_base.collection_best_practices
    data_path = os.path.join(config.knowledge_base.data_dir, "resume_best_practices.json")

    if force:
        builder.clear_collection(collection_name)

    data = load_json(data_path)
    if not data:
        print("  无数据，跳过")
        return

    documents = []
    metadatas = []

    for item in data:
        content_parts = [
            f"简历部分: {item['section']}",
            f"主题: {item['topic']}",
            f"内容: {item['content']}",
        ]
        documents.append("\n".join(content_parts))
        metadatas.append({
            "section": item["section"],
            "topic": item["topic"],
        })

    count = builder.index_documents(collection_name, documents, metadatas)
    print(f"  [{collection_name}] 索引完成: {count} 条")


def build_ats_keywords(builder, force: bool):
    """
    构建 ATS 关键词知识库
    每个岗位的关键词作为一个文档
    """
    config = get_config()
    collection_name = config.knowledge_base.collection_ats_keywords
    data_path = os.path.join(config.knowledge_base.data_dir, "ats_keywords.json")

    if force:
        builder.clear_collection(collection_name)

    data = load_json(data_path)
    if not data:
        print("  无数据，跳过")
        return

    documents = []
    metadatas = []

    for item in data:
        documents.append(f"岗位: {item['role']}\nATS关键词: {item['keywords']}")
        metadatas.append({
            "role": item["role"],
            "keyword_count": len(item["keywords"].split(", ")),
        })

    count = builder.index_documents(collection_name, documents, metadatas)
    print(f"  [{collection_name}] 索引完成: {count} 条")


def main():
    force = "--force" in sys.argv

    print("=" * 50)
    print("AI简历优化Agent - 知识库构建")
    print("=" * 50)

    builder = get_index_builder()
    print(f"Embedding 模型: {builder.embedding_model_name}")
    print(f"Chroma 目录: {builder.persist_dir}")

    print("\n[1/3] 构建技能分类知识库...")
    build_skill_taxonomy(builder, force)

    print("\n[2/3] 构建简历最佳实践知识库...")
    build_best_practices(builder, force)

    print("\n[3/3] 构建 ATS 关键词知识库...")
    build_ats_keywords(builder, force)

    print("\n" + "=" * 50)
    print("知识库构建完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
