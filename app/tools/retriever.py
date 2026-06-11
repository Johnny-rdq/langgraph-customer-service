"""DP 知识库检索工具模块
DP 基于 ChromaDB + 阿里云 Embedding 模型做语义检索。
DP 自动检测 knowledge_base.txt 修改时间，变化时重建向量库。
"""
import os
import logging
import hashlib
from typing import List
from pathlib import Path

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_vector_store = None  # 全局单例
_base_dir = Path(__file__).resolve().parent.parent.parent  # 项目根目录


def _get_kb_hash(kb_path: str) -> str:
    """计算知识库文件的 MD5 哈希，用于检测内容变化"""
    try:
        with open(kb_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return ""


def _get_vector_store() -> Chroma:
    """DP 获取或创建 ChromaDB 向量存储（自动检测知识库更新并重建）"""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    from app.core.config import get_settings
    settings = get_settings()

    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
    )

    chroma_dir = str(_base_dir / "storage" / "chroma_db")
    kb_path = str(_base_dir / settings.KNOWLEDGE_BASE_PATH)
    db_file = os.path.join(chroma_dir, "chroma.sqlite3")
    hash_file = os.path.join(chroma_dir, ".kb_hash")  # 存知识库指纹

    # 检查知识库是否更新过
    current_hash = _get_kb_hash(kb_path)
    old_hash = ""
    needs_rebuild = False

    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            old_hash = f.read().strip()
    if old_hash != current_hash:
        needs_rebuild = True
        logger.info("📝 检测到知识库已更新，将重建向量索引...")
        # 删除旧向量库（文件被占用时跳过，不影响新连接）
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                logger.warning("⚠️ 无法删除旧向量库文件（可能被占用），将清空集合重建")
                # 先创建一个临时连接来清空旧数据
                temp_store = Chroma(
                    collection_name="customer_service_kb",
                    embedding_function=embeddings,
                    persist_directory=chroma_dir,
                )
                try:
                    # 获取所有文档 ID 并删除
                    existing = temp_store.get()
                    if existing and existing.get("ids"):
                        temp_store.delete(ids=existing["ids"])
                        logger.info("✅ 已清空旧向量数据")
                except Exception as e:
                    logger.warning(f"⚠️ 清空旧数据失败: {e}")

    # 连接 ChromaDB
    _vector_store = Chroma(
        collection_name="customer_service_kb",
        embedding_function=embeddings,
        persist_directory=chroma_dir,
    )

    # 需要重建时加载 txt 并灌入
    if needs_rebuild and os.path.exists(kb_path):
        with open(kb_path, "r", encoding="utf-8") as f:
            content = f.read()

        entries = [entry.strip() for entry in content.split("\n\n") if entry.strip()]
        docs = [Document(page_content=entry) for entry in entries]

        if docs:
            _vector_store.add_documents(docs)
            logger.info(f"✅ 成功向量化 {len(docs)} 条知识并存入 ChromaDB")
        else:
            logger.warning("⚠️ 知识库文件为空")

        # 保存新哈希
        os.makedirs(chroma_dir, exist_ok=True)
        with open(hash_file, "w") as f:
            f.write(current_hash)

    elif not os.path.exists(kb_path):
        logger.warning(f"⚠️ 找不到知识库文件: {kb_path}")

    return _vector_store


def retrieve_knowledge(query: str, top_k: int = 3) -> List[str]:
    """DP 语义检索知识库，返回最相关的 top_k 条知识段落"""
    try:
        vector_store = _get_vector_store()
        results = vector_store.similarity_search(query, k=top_k)

        if not results:
            logger.info(f"🔍 语义检索无结果: query='{query[:30]}...'")
            return []

        docs = [doc.page_content for doc in results]
        logger.info(f"🔍 检索命中 {len(docs)} 条: query='{query[:30]}...'")
        return docs

    except Exception as e:
        logger.error(f"❌ 向量检索异常: {e}", exc_info=True)
        return []
