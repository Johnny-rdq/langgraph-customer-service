"""
知识库检索工具模块
提供基于本地知识库文件的 RAG 检索功能

说明: 当前版本使用简单的关键词匹配 (TF-IDF + 余弦相似度) 作为检索方案。
后期可替换为向量数据库 (如 Milvus / Chroma / FAISS) 以支持语义检索。
"""
import os  # 文件路径处理
import logging  # 日志模块
from typing import List  # 类型标注
from sklearn.feature_extraction.text import TfidfVectorizer  # TF-IDF 文本向量化
from sklearn.metrics.pairwise import cosine_similarity  # 余弦相似度计算
import jieba  # 中文分词库，用于提升 TF-IDF 效果

logger = logging.getLogger(__name__)  # 创建日志记录器


# ── 知识库加载与缓存 ──
_knowledge_base_cache: List[str] = []  # 知识库条目列表缓存
_loaded_path: str = ""  # 记录已加载的文件路径，避免重复加载


def _load_knowledge_base(file_path: str) -> List[str]:
    """加载本地知识库文件，按段落分割

    从 txt 文件中读取内容，按空行分割为独立的知识条目。
    使用模块级缓存，同一文件路径不会重复加载。

    Args:
        file_path: 知识库文本文件路径

    Returns:
        知识条目列表，每个元素为一个知识段落
    """
    global _knowledge_base_cache, _loaded_path  # 使用模块级缓存变量

    # 如果已加载同一个文件，直接返回缓存
    if _loaded_path == file_path and _knowledge_base_cache:
        return _knowledge_base_cache

    if not os.path.exists(file_path):  # 检查文件是否存在
        logger.warning(f"⚠️  知识库文件不存在: {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:  # 以 UTF-8 编码打开文件
        content = f.read()  # 读取全部内容

    # 按空行分割为独立知识条目，过滤掉空白条目
    entries = [
        entry.strip() for entry in content.split("\n\n") if entry.strip()
    ]

    # 更新缓存
    _knowledge_base_cache = entries
    _loaded_path = file_path

    logger.info(f"📖 知识库加载完成: {len(entries)} 条知识, 来源: {file_path}")
    return entries


# ── 分词函数 ──
def _tokenize_chinese(text: str) -> str:
    """对中文文本进行分词处理

    使用 jieba 分词将中文文本切分为空格分隔的词语，
    提升 TF-IDF 对中文的检索效果。

    Args:
        text: 原始中文文本

    Returns:
        空格分隔的分词结果
    """
    return " ".join(jieba.cut(text))  # 结巴分词后以空格连接


# ── 检索主函数 ──
def retrieve_knowledge(query: str, top_k: int = 3) -> List[str]:
    """根据用户查询检索最相关的知识条目

    使用 TF-IDF + 余弦相似度进行关键词匹配检索。

    Args:
        query: 用户查询文本
        top_k: 返回最相关的前 K 条知识，默认 3

    Returns:
        相关知识条目文本列表，按相关度降序排列
    """
    from app.core.config import get_settings  # 延迟导入，避免循环依赖

    settings = get_settings()  # 获取全局配置
    kb_path = settings.KNOWLEDGE_BASE_PATH  # 从配置读取知识库路径

    # 加载知识库
    entries = _load_knowledge_base(kb_path)

    if not entries:  # 知识库为空
        logger.warning("⚠️  知识库无内容，返回空结果")
        return []

    # 构建文档列表: [查询] + [知识条目1, 知识条目2, ...]
    all_docs = [query] + entries

    # 对中文进行分词后做 TF-IDF
    tokenized_docs = [_tokenize_chinese(doc) for doc in all_docs]

    # TF-IDF 向量化
    vectorizer = TfidfVectorizer()  # 创建 TF-IDF 向量化器
    tfidf_matrix = vectorizer.fit_transform(tokenized_docs)  # 拟合并转换所有文档

    # 计算查询向量与所有知识条目向量的余弦相似度
    query_vec = tfidf_matrix[0:1]  # 查询向量 (第 0 行)
    entry_vecs = tfidf_matrix[1:]  # 知识条目向量 (第 1 行起)
    similarities = cosine_similarity(query_vec, entry_vecs)[0]  # 计算余弦相似度

    # 按相似度排序，取 top_k
    # 创建 (索引, 相似度) 列表
    scored_indices = list(enumerate(similarities))
    # 按相似度降序排列
    scored_indices.sort(key=lambda x: x[1], reverse=True)

    # 取 top_k 条（过滤掉相似度为 0 的结果）
    top_results = [
        entries[idx]
        for idx, score in scored_indices[:top_k]
        if score > 0  # 只返回有相关度的结果
    ]

    logger.info(
        f"🔍 检索完成: query='{query[:50]}...', "
        f"匹配 {len(top_results)}/{len(entries)} 条"
    )
    return top_results
