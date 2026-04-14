# RAGFlow-DTT 管理后台

RAGFlow-DTT 管理后台是基于 RAGFlow 的独立管理系统，提供组织架构管理、用户管理、知识库管理、文件管理、统计概览等功能。

## 架构概览

```
management/
├── server/                  # 后端 (Python Flask)
│   ├── app.py               # Flask 应用入口，登录鉴权，JWT 签发
│   ├── database.py          # 数据库连接配置 (MySQL/MinIO/ES/Redis)
│   ├── utils.py             # 工具函数 (UUID 生成等)
│   ├── routes/              # 路由层 (Blueprint)
│   │   ├── __init__.py      # 蓝图注册
│   │   ├── teams/           # 组织管理 API
│   │   ├── users/           # 用户管理 API
│   │   ├── knowledgebases/  # 知识库管理 API
│   │   ├── files/           # 文件管理 API
│   │   ├── stats/           # 统计概览 API
│   │   ├── tenants/         # 租户 API
│   │   └── conversation/    # 对话 API
│   ├── services/            # 服务层 (业务逻辑)
│   │   ├── auth/            # 认证服务
│   │   ├── teams/           # 组织服务
│   │   ├── users/           # 用户服务
│   │   ├── knowledgebases/  # 知识库服务
│   │   ├── files/           # 文件服务
│   │   ├── stats/           # 统计服务
│   │   ├── tenants/         # 租户服务
│   │   └── conversation/    # 对话服务
│   ├── scripts/             # 数据库迁移/初始化脚本
│   ├── requirements.txt     # 完整依赖
│   └── requirements-light.txt # 轻量依赖
├── web/                     # 前端 (Vue 3 + Element Plus + Vite)
│   ├── src/
│   │   ├── pages/           # 页面
│   │   │   ├── overview/    # 首页概览 Dashboard
│   │   │   ├── team-management/  # 组织管理 (树形结构)
│   │   │   ├── user-management/  # 用户管理
│   │   │   ├── knowledgebase/    # 知识库管理
│   │   │   ├── file/             # 文件管理
│   │   │   ├── login/            # 登录页
│   │   │   └── ...
│   │   ├── common/apis/     # API 接口定义
│   │   ├── router/          # 路由配置
│   │   ├── layouts/         # 布局组件
│   │   └── pinia/           # 状态管理
│   └── package.json
├── docker-compose.yml       # Docker Compose 编排
└── Dockerfile.light         # 轻量后端 Docker 镜像
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + TypeScript |
| UI 组件库 | Element Plus |
| 构建工具 | Vite |
| 状态管理 | Pinia |
| 后端框架 | Flask (Python 3.10) |
| 数据库 | MySQL (共用 RAGFlow 的 `rag_flow` 数据库) |
| 对象存储 | MinIO |
| 搜索引擎 | Elasticsearch |
| 缓存 | Redis |
| 鉴权 | JWT |
| 容器化 | Docker + Docker Compose |

## 核心功能

### 1. 首页概览 (Dashboard)

路由：`/overview`

统计卡片展示：组织总数、用户总数、知识库总数、文件总数。

API：`GET /api/v1/stats/overview`

### 2. 组织管理

路由：`/team`

- **树形组织架构**：支持无限层级的树形结构展示
- **组织 CRUD**：创建、编辑、删除组织，支持设置上级组织、负责人
- **拖拽调整层级**：整行可拖拽，拖放到目标行即可调整上下级关系
- **成员管理**：查看、添加、移除成员，修改成员角色 (admin/editor/viewer)
- **知识库卡片**：查看组织下的知识库列表，支持创建知识库
- **文件列表**：查看组织下的文件，支持上传文件到指定知识库
- **子孙聚合**：父级组织的成员/知识库/文件数量包含所有子孙组织的数据（成员按 user_id 去重）
- **子孙展示**：成员列表、知识库卡片、文件列表中展示子孙组织的数据，并标注来源组织
- **级联删除**：删除组织时级联软删除所有子组织及成员关联
- **防循环校验**：编辑上级组织时不允许设置为自身或自身的子孙

主要 API：
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/teams/tree` | 获取完整组织树 |
| POST | `/api/v1/teams` | 创建组织 |
| PUT | `/api/v1/teams/<id>` | 编辑组织 |
| DELETE | `/api/v1/teams/<id>` | 删除组织 (级联) |
| GET | `/api/v1/teams/<id>/members` | 获取成员 (含子孙，去重) |
| POST | `/api/v1/teams/<id>/members` | 添加成员 |
| DELETE | `/api/v1/teams/<id>/members/<uid>` | 移除成员 |
| PUT | `/api/v1/teams/<id>/members/<uid>/role` | 修改成员角色 |
| GET | `/api/v1/teams/<id>/knowledgebases` | 获取知识库 (含子孙) |
| GET | `/api/v1/teams/<id>/files` | 获取文件 (含子孙) |

### 3. 用户管理

路由：`/dashboard`

- 用户列表 (分页、搜索)
- 显示用户所属组织
- 角色管理

API：`GET /api/v1/users`

### 4. 知识库管理

路由：`/knowledgebase`

- 知识库列表 (分页、搜索)
- 知识库创建、编辑
- 支持关联组织 (org_id)

API：`GET/POST /api/v1/knowledgebases`

### 5. 文件管理

路由：`/file`

- 文件列表 (分页、搜索)
- 文件上传、解析
- 支持文档解析进度查看

API：`GET /api/v1/files`

## 数据库设计

管理后台共用 RAGFlow 的 `rag_flow` 数据库，主要涉及以下表：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `organization` | 组织表 | id, name, owner_id, parent_id, status |
| `org_member` | 组织成员关联表 | org_id, user_id, role, status |
| `user` | 用户表 | id, nickname, email, status |
| `knowledgebase` | 知识库表 | id, name, org_id, created_by, status |
| `document` | 文档/文件表 | id, name, kb_id, size, status |

### 组织层级关系

通过 `organization.parent_id` 实现树形层级结构：
- `parent_id = NULL` 表示根组织
- 支持无限层级嵌套
- 删除时级联软删除所有子孙节点

## 部署

### Docker Compose 部署

```bash
# 在 management/ 目录下
docker-compose up -d
```

服务端口：
- 前端：`8888` (Nginx 代理)
- 后端：`5000` (Flask)

### 构建前端

```bash
cd management/web
npm install
npx vite build
```

构建产物输出到 `management/web/dist/`。

### 手动部署到 Docker 容器

```bash
# 前端
docker cp dist/. ragflowdtt-management-frontend:/usr/share/nginx/html/

# 后端
docker cp server/. ragflowdtt-management-backend:/app/
docker restart ragflowdtt-management-backend
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MANAGEMENT_ADMIN_USERNAME` | admin | 管理员用户名 |
| `MANAGEMENT_ADMIN_PASSWORD` | 12345678 | 管理员密码 |
| `MANAGEMENT_JWT_SECRET` | your-secret-key | JWT 签名密钥 |
| `MYSQL_PASSWORD` | infini_rag_flow | MySQL 密码 |
| `MINIO_USER` | rag_flow | MinIO 用户名 |
| `MINIO_PASSWORD` | infini_rag_flow | MinIO 密码 |
| `ELASTIC_USER` | elastic | ES 用户名 |
| `ELASTIC_PASSWORD` | infini_rag_flow | ES 密码 |

## 前端路由

| 路由 | 页面 | 角色权限 |
|------|------|----------|
| `/overview` | 首页概览 | admin, team_owner |
| `/team` | 组织管理 | admin, team_owner |
| `/dashboard` | 用户管理 | admin |
| `/knowledgebase` | 知识库管理 | admin, team_owner |
| `/file` | 文件管理 | admin, team_owner |
| `/login` | 登录 | 公开 |

## 鉴权机制

- 登录接口：`POST /api/v1/auth/login`
- 返回 JWT token，有效期 1 小时
- 前端在 Authorization header 中携带 token
- 后端通过 `get_current_user_from_token()` 解析当前用户
- 角色：`admin` (超级管理员) / `team_owner` (团队负责人)
