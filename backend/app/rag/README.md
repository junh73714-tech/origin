# 成员6 RAG / LangGraph 问答模块

## 流程

接收问题 → AccessContext 快照 → 预处理 → 标准问答匹配 →
（可信命中返回 / 否则）混合检索 → Rerank → 证据覆盖 → 上下文组装 →
生成或拒答 → 引用二次鉴权 → 返回

## 组件

| 路径 | 说明 |
|------|------|
| `state.py` | 可序列化 RAGState |
| `graph.py` | 正式问答图（LangGraph 风格节点流水线） |
| `preprocess.py` | 清洗、改写、意图、关键词、实体 |
| `evidence.py` | 证据覆盖度 |
| `context_builder.py` | Token 预算与 citation_id |
| `standard_qa_adapter.py` | 成员7匹配服务适配 |

## Provider

- LLM / Reranker：抽象 + Mock（真实服务未绑定，硬阻塞）
- Embedding：确定性测试替身，维度对齐 `EMBEDDING_DIMENSION`，正式应替换为成员5 Provider

## 提示词版本

`prompts/qa_system.py` 中 `PROMPT_VERSION=qa-prompt-v1`

## 测试

```bash
cd backend
pytest tests/rag -v
```
