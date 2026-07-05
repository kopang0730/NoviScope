# NoviScope 技术栈与 Web MVP 实现设计

日期：2026-07-05  
状态：设计/计划稿  
范围：技术栈定稿、Admin-managed Lab Alpha、Web MVP 边界、前后端实现顺序  

## 1. 结论

NoviScope 的 MVP 技术栈应保持轻量，但主部署目标已经调整为组内多人使用：服务器管理员集中部署，用户通过邀请码注册登录。第一版需要把认证、邀请码、PostgreSQL、共享/个人 provider、科研任务创建、阶段推进、人工复核和证据展示跑通。不要在 MVP 阶段过早引入完整前端组件库、复杂队列系统、完整 Docker 化实验环境或自动 GPU 实验执行。

MVP 技术栈：

```text
Frontend: React + TypeScript + Vite + Tailwind CSS
Backend: FastAPI + Pydantic + SQLModel
Database: PostgreSQL for lab deployment, SQLite only for development/test
Auth: invite-code registration + login/session + admin/member roles
Worker: DB-backed simple worker loop
Model Gateway: httpx + OpenAI-compatible / Anthropic / custom adapter
Provider Scope: admin-shared providers + user-personal providers
Artifacts: local filesystem
Experiment Runtime: host-level shell/tmux/conda/uv runner
Deployment: admin-managed Linux server, Caddy/Nginx, Docker Compose later
```

Lab Beta 技术栈：

```text
Frontend: React + TypeScript + Vite + Tailwind + shadcn/ui where useful
Backend: FastAPI
Database: PostgreSQL
Worker Queue: Redis + RQ or Dramatiq
Log Streaming: Server-Sent Events
Reverse Proxy: Caddy or Nginx
Deployment: Docker Compose for service layer
Experiment Runtime: host-level runner first, optional Docker runner later
```

## 2. 技术栈原则

- 保持 MVP 可理解：先让组内成员通过登录系统跑通完整使用路径。
- 保持后端连续性：沿用已经实现的 FastAPI、SQLModel、provider、quest、stage 基础。
- 保持前端轻量：先做可用的研究任务界面，不做通用 IDE 或复杂设计系统。
- 保持实验环境现实：CV baseline 依赖复杂，实验 runner 先使用宿主机环境，不强制 Docker 化。
- 保持部署职责清晰：管理员部署服务，普通用户只注册登录和使用 Web。
- 保持升级路径清晰：simple worker、host runner、basic roles 都是 MVP 选择，不是长期上限。

## 3. 重新评估后的取舍

### 3.1 不采用 Next.js 作为 MVP 前端

NoviScope MVP 不需要 SSR、复杂路由、服务端渲染缓存或内容站能力。React + Vite 产出静态资源，再由 FastAPI 或简单静态服务托管即可。这样部署更直接，也更适合 A800 Linux 服务器的内网使用。

### 3.2 暂不强依赖 shadcn/ui

shadcn/ui 适合产品形态稳定后的 UI 体系，但 MVP 当前只有任务列表、表单、阶段卡片、详情页和复核卡片。先用 Tailwind + 少量自写基础组件可以降低维护成本。等页面结构稳定后，再按需引入 shadcn/ui 的 Dialog、Tabs、Table、Select、Toast 等组件。

### 3.3 暂不引入 Redis 队列

第一版后台任务可以通过数据库状态和 simple worker loop 实现：

```text
stage.status = pending
worker polls pending stages
worker marks running
worker writes output/evidence/artifacts
worker marks complete/blocked
```

当出现并发任务、失败重试、任务取消、日志流和多 worker 调度需求时，再升级 Redis + RQ 或 Dramatiq。

### 3.4 PostgreSQL 作为组内部署数据库

SQLite 仅用于开发和测试。组内 Alpha 从一开始就使用 PostgreSQL。原因是当前目标已经明确为多用户登录、邀请码注册、quest ownership、provider scope、审计日志和后续 worker 状态更新。继续把 SQLite 作为组内部署数据库会让后续迁移成本变高。

### 3.5 服务层可以 Docker 化，实验层先不强制 Docker 化

NoviScope 服务层最终可以用 Docker Compose 管理 API、Web、DB、Queue、Proxy。但 CV 实验仓库往往有各自的 CUDA、PyTorch、mmcv、conda 和系统依赖。MVP 的实验 runner 应优先支持宿主机环境、tmux/screen、conda/uv 和固定工作目录。

## 4. Web MVP 用户范围

MVP 面向三类用户：

1. Admin：部署后管理邀请码、共享 provider、用户和系统配置。
2. Member：通过邀请码注册登录，创建研究任务，查看阶段，做人工复核。
3. 管理/开发用户：通过 CLI 启动服务、检查环境、运行 worker、导出任务产物。

MVP 不要求普通用户理解数据库、worker、端口、队列、SSH 或实验命令细节。

## 5. Web MVP 页面

### 5.1 Login

目标：让已注册用户进入系统。

字段：

- email
- password

行为：

- 登录成功后进入 quest list
- 登录失败时显示明确错误
- 未登录用户不能访问 quest、provider、admin 页面

### 5.2 Invitation Registration

目标：让组内成员通过邀请码注册。

字段：

- invite code
- email
- display name
- password
- confirm password

行为：

- 邀请码只能使用一次或按配置限制次数
- 注册后默认角色为 member
- 首个 bootstrap admin 由部署配置或 CLI 创建，不通过普通邀请码产生

### 5.3 Home / Quest List

目标：让用户看到当前所有研究任务。

显示：

- quest title
- initial direction
- current status
- current stage
- pending review count
- updated time

主要操作：

- create quest
- open quest

权限：

- member 默认只看自己的 quest
- admin 可以看全部 quest

### 5.4 Create Quest

目标：让用户用最少信息启动研究任务。

字段：

- title
- initial direction
- language preference: Chinese, English, both
- research mode: conservative, balanced, exploratory
- optional scenario clues
- optional compute budget

提交后：

- 调用 `POST /quests`
- 创建第一张 `demand_validator` stage card
- 跳转到 quest stage board
- quest 绑定当前登录用户为 owner

### 5.5 Provider Settings

目标：让用户查看可用模型配置，并管理自己的 personal provider。

字段：

- provider name
- provider kind
- base URL
- default model
- API key
- optional headers

行为：

- API key 只写入，不回显
- 列表页显示 provider 是否可用
- MVP 可先不做真实连接测试，后续补 `test_connection`
- member 可见 admin-shared provider 和自己的 personal provider
- member 不能查看其他用户的 personal provider

### 5.6 Admin Invite Management

目标：让管理员创建和管理邀请码。

显示：

- invite code
- status
- max uses
- used count
- expires at
- created by

主要操作：

- create invite
- disable invite
- copy invite code

### 5.7 Admin Shared Provider Management

目标：让管理员配置全组可用模型。

行为：

- admin 创建 shared provider
- admin 可以禁用 shared provider
- shared provider 可被所有 member 使用
- shared provider 的 API key 仍然加密保存且不回显

### 5.8 Agent Assignment

目标：让用户选择单模型模式或高级 agent-to-model 绑定。

MVP 默认：

- single provider mode
- 所有 agent 使用一个可见 provider
- 可见 provider 包括 admin-shared provider 和当前用户的 personal provider

高级模式：

- demand validator provider
- literature scout provider
- code runner provider
- evidence auditor provider
- paper writer provider

高级模式可以后置，不阻塞 Web MVP 第一版。

### 5.9 Quest Stage Board

目标：让用户理解任务推进到哪里。

显示 9 个阶段：

1. Demand Validator
2. Research Refiner
3. Literature Scout
4. Gap Analyst
5. Idea Generator
6. Experiment Planner
7. Code Runner
8. Evidence Auditor
9. Paper & Meeting Writer

每个阶段显示：

- status
- summary
- assigned agent
- human approval state
- last updated time
- blocking risk count

### 5.10 Stage Detail

目标：展示一个阶段的输入、输出、证据和操作。

显示：

- stage metadata
- input payload
- output payload
- evidence payload
- review notes
- artifact links
- raw JSON collapsible view

主要操作：

- mark running
- mark complete
- mark blocked
- approve
- revise
- reject

MVP 可以先把 stage update 作为人工操作，后续再接入真实 agent execution。

### 5.11 Human Review Card

目标：让用户在关键节点做清晰决策。

卡片应显示：

- system recommendation
- confidence
- evidence summary
- risks
- what happens if approved
- what happens if rejected

操作：

- approve
- request revision
- reject/archive
- add review notes

## 6. 前端架构

建议目录：

```text
web/
  package.json
  index.html
  vite.config.ts
  src/
    main.tsx
    app.tsx
    api/
      client.ts
      auth.ts
      invites.ts
      providers.ts
      quests.ts
      agents.ts
    components/
      button.tsx
      input.tsx
      textarea.tsx
      badge.tsx
      card.tsx
      table.tsx
      json-view.tsx
    pages/
      login.tsx
      register.tsx
      quest-list.tsx
      create-quest.tsx
      provider-settings.tsx
      admin-invites.tsx
      admin-shared-providers.tsx
      agent-assignment.tsx
      quest-board.tsx
      stage-detail.tsx
    styles/
      globals.css
```

MVP 不需要复杂状态管理库。用 React state、React Router 和小型 API client 即可。等页面复杂后再考虑 TanStack Query。

## 7. 后端边界

MVP Web 应优先复用已有 API：

- `GET /health`
- `GET /agents`
- `POST /providers`
- `GET /providers`
- `GET /providers/{provider_id}`
- `PATCH /providers/{provider_id}`
- `DELETE /providers/{provider_id}`
- `POST /quests`
- `GET /quests/{quest_id}/stages`
- `PATCH /stages/{stage_id}`

需要补充的后端 API：

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /admin/invites`
- `GET /admin/invites`
- `PATCH /admin/invites/{invite_id}`
- `GET /quests`
- `GET /quests/{quest_id}`
- `PATCH /quests/{quest_id}`
- `GET /agent-assignments`
- `PATCH /agent-assignments/{agent_key}`
- provider scope and ownership fields for shared/personal providers

Web MVP 可以先不实现真实 agent 自动执行。它先做人工 stage 操作和数据可视化，保证 quest/stage/provider 基础闭环可用。

新增访问控制规则：

- 未登录用户只能访问登录、注册和健康检查。
- member 默认只能访问自己的 quest。
- admin 可以访问所有 quest。
- shared provider 对所有已登录用户可见。
- personal provider 只对 owner 和 admin 可见。
- API 响应永远不返回 provider API key 或密文。

## 8. Worker MVP

第一版 worker 不进入 Web MVP 的最小范围。Web MVP 先支持人工推进 stage。

第二步再增加 simple worker：

```text
noviscope worker
  -> scan executable pending stage
  -> acquire stage lock
  -> run stage handler
  -> write output_payload/evidence_payload
  -> update status
```

simple worker 的约束：

- 同一 stage 只能被一个 worker 执行
- 每次执行都写 execution record
- 失败要写 blocked reason
- 不自动绕过 human review gate
- 不上传私有文件到外部模型 API

## 9. Artifact 存储

MVP 使用本地文件系统：

```text
.noviscope/
  artifacts/
    quests/
      <quest-id>/
        stages/
          <stage-id>/
            report.md
            evidence.json
            logs/
            figures/
            exports/
```

数据库保存 artifact metadata：

- artifact id
- quest id
- stage id
- path
- type
- created at
- hash if available
- visibility

第一版可以先展示路径和基本 metadata，不急于做完整 artifact browser。

## 10. 实验运行策略

MVP Web 不直接跑 GPU 实验。实验执行进入后续阶段。

实验 runner 的推荐策略：

```text
host shell runner first
tmux/screen for long jobs
conda/uv support
fixed working directory
command logging
stdout/stderr capture
environment snapshot
no private upload by default
```

后续可以增加 Docker runner，但不把 Docker 作为唯一运行方式。

## 11. 实施计划

### Phase 1: Auth and Lab Access

目标：管理员部署后，用户可以通过邀请码注册登录。

任务：

- add PostgreSQL configuration path
- add user model
- add invite code model
- add password hashing
- add login/session or JWT
- add admin/member roles
- add bootstrap admin mechanism
- add auth API tests
- implement login page
- implement invitation registration page

验收：

- admin can create invitation codes
- user can register only with a valid invitation code
- user can log in and log out
- unauthenticated users cannot access protected APIs
- password is never stored in plaintext

### Phase 2: Web Shell

目标：浏览器可操作已有后端核心对象。

任务：

- create `web/` Vite React project
- add Tailwind CSS
- build API client
- implement quest list
- implement create quest
- implement provider settings
- implement quest stage board
- implement stage detail
- serve frontend in development through Vite proxy

验收：

- 用户能从浏览器创建 quest
- 用户能查看 stage
- 用户能更新 stage status、summary、evidence、review notes
- quest 绑定当前登录用户
- provider API key 不会在 UI 中回显

### Phase 3: Provider Scope and Backend Gaps

目标：补齐 Web 需要但后端尚未提供的列表、详情、权限和 provider scope。

任务：

- add `GET /quests`
- add `GET /quests/{quest_id}`
- add quest update endpoint if needed
- add agent assignment read/update endpoints
- add shared/personal provider scope
- enforce provider visibility rules
- add admin shared provider management endpoints
- add API response tests

验收：

- quest list 页面不需要 mock 数据
- agent assignment 页面可以读写真实后端数据
- member can use shared provider
- member can use own personal provider
- member cannot read another user's personal provider
- admin can manage shared provider
- `pytest` 通过

### Phase 4: Admin-Managed Deployment

目标：管理员能在 Linux 服务器上部署，用户通过组内 Web 地址访问。

任务：

- build static frontend
- mount static assets in FastAPI
- add CLI command `noviscope serve`
- add `.env.example` for PostgreSQL, secret keys, bootstrap admin, artifacts
- add service-layer Docker Compose or documented venv deployment
- document Caddy/Nginx reverse proxy path
- keep SSH tunnel as development mode documentation

验收：

- admin can deploy NoviScope on the lab server
- user can open the lab URL from a browser
- refresh browser route works
- `/api` endpoints still work

### Phase 5: Simple Worker Skeleton

目标：为后续自动 stage execution 做最小 worker 基础。

任务：

- add worker command
- add stage execution lease fields if needed
- add execution log model if needed
- add one no-op or stub handler
- make worker write blocked/completed status deterministically

验收：

- worker can pick a test pending stage
- worker writes stage output
- worker does not bypass human approval gate

## 12. 测试策略

后端：

- pytest for API endpoints
- pytest for auth and invitation code flow
- pytest for quest/stage transition rules
- pytest for provider key redaction
- pytest for agent assignment behavior
- pytest for provider visibility rules

前端：

- TypeScript build must pass
- basic component tests can wait until UI stabilizes
- Playwright smoke test should be added once static serving exists

人工验收：

- register with invitation code
- log in and log out
- create provider
- create quest
- view quest board
- open stage detail
- approve/reject/revise a stage
- confirm API key is never displayed
- confirm member cannot see another user's quest
- confirm admin can create shared provider
- confirm lab URL access works

## 13. 非目标

Web MVP 不做：

- 完整论文编辑器
- 复杂图数据库可视化
- WebSocket 实时协作
- 复杂多租户权限系统
- 公开 SaaS 部署
- 自动 GPU 实验运行
- 完整 agent 自动执行
- 完整 shadcn/ui 设计系统

这些能力应在 Web MVP 证明可用之后分阶段实现。

## 14. 风险和缓解

### 风险：Web 页面过早复杂化

缓解：第一版只做登录、注册、任务、provider、admin 管理和 stage 审核相关页面，优先使用表格、卡片和可折叠 JSON。

### 风险：用户被模型配置劝退

缓解：管理员先配置 shared provider，普通用户可以直接选择共享模型。个人 provider 和高级 agent assignment 后置。

### 风险：登录和权限让第一版变重

缓解：只做 admin/member 两级角色和邀请码注册，不做组织、团队、项目级复杂 ACL。

### 风险：PostgreSQL 增加部署门槛

缓解：Docker Compose 或清晰的 `.env.example` 管理数据库配置；SQLite 继续保留为开发和测试路径。

### 风险：实验运行污染服务环境

缓解：实验 runner 使用独立 working directory，不在 Web MVP 阶段直接执行高风险代码。

### 风险：文档和实现漂移

缓解：Web MVP 每个阶段完成后更新 README 和本设计文档中的状态说明，PR 描述必须引用验收方式。

## 15. 成功标准

Web MVP 成功不是页面完整，而是用户可以完成一条可见的最小科研任务路径：

```text
register/login
-> configure provider
-> create quest
-> inspect demand_validator stage
-> write evidence payload
-> approve/reject stage
-> see quest state change
```

这条路径跑通后，再接入真实文献检索、需求验证 agent、后台 worker 和实验 runner。
