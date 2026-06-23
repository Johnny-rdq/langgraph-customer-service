"""
知识库检索工具模块
基于 LlamaIndex 做语义检索，集成 HyDE 查询变换 + 语义分句切分。
自动检测 knowledge_base.txt 修改，变化时重建索引。
"""
import os
import logging
import hashlib
import shutil
from typing import List
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine

logger = logging.getLogger(__name__)

_index = None  # 全局单例索引
_base_dir = Path(__file__).resolve().parent.parent.parent  # 项目根目录


def _get_kb_hash(kb_path: str) -> str:
    """计算知识库文件的 MD5 哈希，用于检测内容变化"""
    try:
        with open(kb_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def _get_index() -> VectorStoreIndex:
    """获取或创建 LlamaIndex 索引（自动检测知识库更新并重建）

    LlamaIndex 管理全流程：
    1. 文档加载 → 语义分句切分（SentenceSplitter）
    2. 向量化（阿里云百炼 text-embedding-v2）
    3. 索引持久化（storage/llama_index/）
    4. 查询时 HyDE 假设答案增强（HyDEQueryTransform）
    """
    global _index
    if _index is not None:
        return _index

    from app.core.config import get_settings
    settings = get_settings()

    # ── 配置全局 LLM（HyDE 查询变换需要用 LLM 生成"假设答案"）──
    from llama_index.llms.openai_like import OpenAILike
    Settings.llm = OpenAILike(
        model=settings.LLM_MODEL,
        api_base=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        is_chat_model=True,
    )

    # ── 配置全局 Embedding 模型（文本向量化）──
    from langchain_community.embeddings import DashScopeEmbeddings
    from llama_index.embeddings.langchain import LangchainEmbedding
    lc_embed = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )
    Settings.embed_model = LangchainEmbedding(lc_embed)

    # ── 配置文档切分器（按语义分句，比手动 \n\n 分段精细得多）──
    Settings.node_parser = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=64,
    )

    persist_dir = str(_base_dir / "storage" / "llama_index")
    kb_path = str(_base_dir / settings.KNOWLEDGE_BASE_PATH)
    hash_file = os.path.join(persist_dir, ".kb_hash")

    # ── 检查知识库是否更新（MD5 指纹对比）──
    current_hash = _get_kb_hash(kb_path)
    old_hash = ""
    needs_rebuild = False

    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            old_hash = f.read().strip()
    if old_hash != current_hash:
        needs_rebuild = True
        logger.info("[NOTE] 检测到知识库已更新，将重建 LlamaIndex 索引...")
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)

    os.makedirs(persist_dir, exist_ok=True)

    if needs_rebuild and os.path.exists(kb_path):
        # ── 加载文档：按 \n\n 粗分段为 Document，再交给 SentenceSplitter 精细切分 ──
        with open(kb_path, "r", encoding="utf-8") as f:
            content = f.read()
        entries = [entry.strip() for entry in content.split("\n\n") if entry.strip()]
        docs = [Document(text=entry) for entry in entries]

        # ── 创建索引：LlamaIndex 自动完成 分句 → 向量化 → 建索引 ──
        _index = VectorStoreIndex.from_documents(docs, show_progress=True)
        _index.storage_context.persist(persist_dir=persist_dir)
        logger.info(f"[OK] LlamaIndex 索引创建完成，共 {len(docs)} 个文档")

        # ── 保存哈希指纹 ──
        with open(hash_file, "w") as f:
            f.write(current_hash)
    else:
        # ── 从磁盘加载已有索引 ──
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        _index = load_index_from_storage(storage_context)
        logger.info("[OK] 从磁盘加载 LlamaIndex 索引")

    return _index


def retrieve_knowledge(query: str, top_k: int = 3) -> List[str]:
    """语义检索知识库，返回最相关的 top_k 条知识段落

    使用 HyDE（Hypothetical Document Embeddings）查询变换增强检索：
    1. LLM 先根据用户问题生成一份"假设答案"
    2. 用假设答案的向量 + 原始问题向量 联合检索
    3. 能显著提升短查询、模糊问题的召回率（如"退货要多久"这类口语化问题）

    Args:
        query: 用户查询文本
        top_k: 返回最相关条数，默认 3
    Returns:
        知识段落文本列表，异常时返回空列表
    """
    try:
        index = _get_index()

        # ── HyDE 查询变换：生成假设答案辅助检索 ──
        hyde = HyDEQueryTransform(include_original=True)
        base_engine = index.as_query_engine(similarity_top_k=top_k)
        query_engine = TransformQueryEngine(
            query_engine=base_engine,
            query_transform=hyde,
        )

        response = query_engine.query(query)
        source_nodes = response.source_nodes
        docs = [node.text for node in source_nodes]

        logger.info(f"[SEARCH] LlamaIndex + HyDE 检索命中 {len(docs)} 条: query='{query[:30]}...'")
        return docs
    except Exception as e:
        logger.error(f"[ERROR] LlamaIndex 检索异常: {e}", exc_info=True)
        return []
