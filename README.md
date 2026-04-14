<div align="center">
  <img src="web/public/logo-dtt.png" width="300" alt="Ragflow-DTT">
  <h1>Ragflow-DTT</h1>
  <p>基于 Ragflow-DTT 的电力行业知识图谱引擎</p>
</div>

<div align="center">
  <img src="https://img.shields.io/badge/版本-0.5.0--dtt-blue" alt="版本">
  <a href="LICENSE"><img src="https://img.shields.io/badge/许可证-AGPL3.0-green" alt="许可证"></a>
</div>

---

## 简介

Ragflow-DTT 是面向电力行业的知识图谱与智能问答平台，基于 [Ragflow-Plus](https://github.com/zstar1003/ragflow-plus) v0.5.0 二次开发，针对电力行业场景进行了深度定制。

### 核心能力

- **GraphRAG 知识图谱** - 实体/关系提取、Leiden 社区检测、PageRank 排序、图谱可视化
- **文档智能解析** - 基于 MinerU 的 PDF/Word/Excel/PPT/图片 OCR 解析，支持版面分析
- **RAG 智能问答** - 混合检索（BM25 + 向量）、重排序、LLM 流式生成、引用标注
- **管理后台** - 用户/团队/知识库/对话/文档全生命周期管理
- **多模型适配** - OpenAI/DeepSeek/Qwen/Ollama/BAAI-BGE 等

### DTT 定制增强

| 功能 | 说明 |
|------|------|
| 图谱可视化增强 | 全屏浏览器、实体详情面板、关系过滤、社区聚类高亮 |
| MinerU 解析器配置 | OCR 开关、分块参数、表格策略、公式识别、自定义分割规则 |
| 问答评测体系 | 评测数据集管理、BLEU/ROUGE-L/关键词覆盖率评分、准确率报表 |
| 品牌定制 | 大唐集团 Logo/Favicon、项目名 Ragflow-DTT |

---

## 技术架构

```
┌─────────────────────────────────────────────────┐
│                   Nginx (80/443)                │
├───────────────┬────────────────┬────────────────┤
│ React前端     │ Vue3管理后台   │ SDK/OpenAI兼容 │
│ UmiJS + Antd  │ Element Plus   │  RESTful API   │
├───────────────┴────────────────┴────────────────┤
│              Flask API Server (9380)            │
│  知识库│文档│对话│Agent│GraphRAG│评测            │
├───────────┬──────────┬──────────┬───────────────┤
│ MySQL 8.0 │ ES 8.11  │ MinIO   │ Redis/Valkey  │
│ 元数据ORM │ 向量+全文│ 文件存储│ 缓存+任务队列 │
├───────────┴──────────┴──────────┴───────────────┤
│           Task Executor (后台进程)              │
│  文档解析(MinerU)→分块→嵌入→GraphRAG→写入ES    │
├─────────────────────────────────────────────────┤
│          LLM Factory (多模型适配)               │
│  OpenAI/DeepSeek/Qwen/Ollama/BAAI-BGE          │
└─────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端(用户端) | React 18 + UmiJS 4 + Ant Design 5 + TailwindCSS |
| 前端(管理端) | Vue 3 + Vite + Element Plus + Pinia |
| 后端API | Python Flask + Peewee ORM + JWT |
| 文档解析 | MinerU (magic-pdf) + OCR/布局分析 |
| 向量搜索 | Elasticsearch 8.11 混合搜索 |
| 知识图谱 | GraphRAG (实体/关系提取 + Leiden + PageRank) |
| 嵌入模型 | BAAI/bge-large-zh-v1.5 (默认) |
| 存储 | MySQL 8.0 + Elasticsearch + MinIO + Redis |
| 部署 | Docker Compose |

---

## 快速部署

### 环境要求

- Linux (Ubuntu 20.04+)
- Docker 20.10+
- Docker Compose v2
- 8+ vCPU / 16+ GB RAM / 100+ GB 磁盘

### 部署步骤

```bash
# 1. 克隆仓库
git clone https://github.com/honghaifeng/ragflow-dtt.git
cd ragflow-dtt/docker

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置密码和配置

# 3. 启动核心服务
docker compose --profile cpu --profile elasticsearch up -d

# 4. 启动管理后台
cd ../management
docker compose up -d

# 5. 访问服务
# 前端: http://your-ip:80
# 管理后台: http://your-ip:8888
# API: http://your-ip:9380
```

### 默认端口

| 服务 | 端口 |
|------|------|
| Nginx (前端) | 80 |
| API Server | 9380 |
| 管理后台 | 8888 |
| MySQL | 5455 |
| Elasticsearch | 1200 |
| MinIO Console | 9001 |

---

## 项目结构

```
ragflow-dtt/
├── api/                    # Flask 后端 API
│   ├── apps/              # 路由模块
│   │   ├── kb_app.py      # 知识库
│   │   ├── dialog_app.py  # 对话
│   │   ├── evaluation_app.py  # 问答评测 (DTT新增)
│   │   └── ...
│   └── db/                # 数据库模型
├── web/                   # React 前端
│   ├── src/pages/
│   │   ├── add-knowledge/ # 知识库详情
│   │   │   └── components/knowledge-graph/  # 图谱可视化 (DTT增强)
│   │   ├── evaluation/    # 问答评测页面 (DTT新增)
│   │   └── ...
│   └── public/            # 静态资源 (Logo/Favicon)
├── management/            # Vue3 管理后台
├── graphrag/              # GraphRAG 模块
├── deepdoc/               # 文档解析
├── docker/                # Docker 部署配置
└── rag/                   # RAG 核心模块
```

---

## 许可证

本项目基于 [AGPLv3](LICENSE) 许可证开源，继承自 Ragflow-DTT / RAGFlow。
