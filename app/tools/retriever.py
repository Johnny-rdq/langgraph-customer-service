"""
知识库检索工具模块 (向量升级版)
提供基于 ChromaDB + 阿里云 Embedding 模型的语义检索功能
"""
import os
import logging
from typing import List
from pathlib import Path

# 导入向量检索核心库
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# 全局单例，避免每次对话都重复连接数据库
_vector_store = None

def _get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    from app.core.config import get_settings
    settings = get_settings()

    # 1. 实例化阿里云 Embedding 模型 (它负责把文字变成数字向量)
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",  # 阿里云最新的通用文本向量模型
        dashscope_api_key=settings.DASHSCOPE_API_KEY
    )

    # 2. 规划数据库存储路径 (存放在我们之前建的 storage 文件夹里)
    base_dir = Path(__file__).resolve().parent.parent.parent
    chroma_persist_dir = str(base_dir / "storage" / "chroma_db")
    kb_path = str(base_dir / settings.KNOWLEDGE_BASE_PATH)

    # 3. 连接或创建 Chroma 向量数据库
    _vector_store = Chroma(
        collection_name="customer_service_kb",
        embedding_function=embeddings,
        persist_directory=chroma_persist_dir
    )

    # 4. 自动数据灌入机制 (如果库里没数据，就自动读取 txt 文件并存入)
    db_file = os.path.join(chroma_persist_dir, "chroma.sqlite3")
    if not os.path.exists(db_file):
        logger.info("📦 首次运行：正在将知识库进行向量化并存入 ChromaDB，请稍候...")
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 按空行切分知识段落
            entries = [entry.strip() for entry in content.split("\n\n") if entry.strip()]
            # 转化为 LangChain 标准文档格式
            docs = [Document(page_content=entry) for entry in entries]

            if docs:
                _vector_store.add_documents(docs)
                logger.info(f"✅ 成功将 {len(docs)} 条知识存入向量数据库！")
        else:
            logger.warning(f"⚠️ 找不到知识库文件: {kb_path}")

    return _vector_store

def retrieve_knowledge(query: str, top_k: int = 3) -> List[str]:
    """根据用户查询，进行高维语义检索"""
    try:
        vector_store = _get_vector_store()

        # 使用相似度检索 (Semantic Similarity Search)
        results = vector_store.similarity_search(query, k=top_k)

        # 提取结果里的纯文本
        docs = [doc.page_content for doc in results]

        logger.info(f"🔍 语义检索完成: query='{query[:15]}...', 匹配到 {len(docs)} 条相关知识")
        return docs

    except Exception as e:
        logger.error(f"❌ 向量检索失败: {e}", exc_info=True)
        return []