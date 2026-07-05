# NoviScope 技术栈与 Web MVP 实现设计

日期：2026-07-05  
状态：设计/计划稿  
范围：技术栈定稿、Web MVP 边界、前后端实现顺序  

## 1. 结论

NoviScope 的 MVP 技术栈应保持轻量，优先把科研任务创建、阶段推进、人工复核、证据展示和 provider 配置跑通。不要在 MVP 阶段过早引入完整前端组件库、复杂队列系统、完整 Docker 化实验环境或多人权限系统。

MVP 技术栈：

```text
Frontend: React + TypeScript + Vite + Tailwind CSS
Backend: FastAPI + Pydantic + SQLModel
Database: SQLite
Worker: DB-backed simple worker loop
Model Gateway: httpx + OpenAI-compatible / Anthropic / custom adapter
Artifacts: local filesystem
Experiment Runtime: host-level shell/tmux/conda/uv runner
Deployment: Linux server + SSH tunnel
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

- 保持 MVP 可理解：先让少数用户在组内服务器上跑通完整使用路径。
- 保持后端连续性：沿用已经实现的 FastAPI、SQLModel、provider、quest、stage 基础。
- 保持前端轻量：先做可用的研究任务界面，不做通用 IDE 或复杂设计系统。
- 保持实验环境现实：CV baseline 依赖复杂，实验 runner 先使用宿主机环境，不强制 Docker 化。
- 保持升级路径清晰：SQLite、simple worker、SSH tunnel 都是 MVP 选择，不是长期上限。

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

### 3.4 SQLite 仅用于 MVP 和单机测试

SQLite 适合开发和早期单机部署，但 Lab Beta 应切换到 PostgreSQL。原因是后续会有多人访问、任务并发、审计日志、artifact metadata、provider assignment、worker lease 和实验状态频繁更新。

### 3.5 服务层可以 Docker 化，实验层先不强制 Docker 化

NoviScope 服务层最终可以用 Docker Compose 管理 API、Web、DB、Queue、Proxy。但 CV 实验仓库往往有各自的 CUDA、PyTorch、mmcv、conda 和系统依赖。MVP 的实验 runner 应优先支持宿主机环境、tmux/screen、conda/uv 和固定工作目录。

## 4. Web MVP 用户范围

MVP 面向两类用户：

1. 普通科研用户：打开网页，配置模型，创建研究任务，查看阶段，做人工复核。
2. 管理/开发用户：通过 CLI 启动服务、检查环境、运行 worker、导出任务产物。

MVP 不要求普通用户理解数据库、worker、端口、队列或实验命令细节。

## 5. Web MVP 页面

### 5.1 Home / Quest List

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

### 5.2 Create Quest

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

### 5.3 Provider Settings

目标：让用户配置模型 API。

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

### 5.4 Agent Assignment

目标：让用户选择单模型模式或高级 agent-to-model 绑定。

MVP 默认：

- single provider mode
- 所有 agent 使用同一 provider

高级模式：

- demand validator provider
- literature scout provider
- code runner provider
- evidence auditor provider
- paper writer provider

高级模式可以后置，不阻塞 Web MVP 第一版。

### 5.5 Quest Stage Board

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

### 5.6 Stage Detail

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

### 5.7 Human Review Card

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
      quest-list.tsx
      create-quest.tsx
      provider-settings.tsx
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

- `GET /quests`
- `GET /quests/{quest_id}`
- `PATCH /quests/{quest_id}`
- `GET /agent-assignments`
- `PATCH /agent-assignments/{agent_key}`

Web MVP 可以先不实现真实 agent 自动执行。它先做人工 stage 操作和数据可视化，保证 quest/stage/provider 基础闭环可用。

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
  noviscope.db
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

### Phase 1: Web Shell

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
- provider API key 不会在 UI 中回显

### Phase 2: Backend Gaps for Web

目标：补齐 Web 需要但后端尚未提供的列表和详情接口。

任务：

- add `GET /quests`
- add `GET /quests/{quest_id}`
- add quest update endpoint if needed
- add agent assignment read/update endpoints
- add API response tests

验收：

- quest list 页面不需要 mock 数据
- agent assignment 页面可以读写真实后端数据
- `pytest` 通过

### Phase 3: Bundle and SSH Tunnel MVP

目标：能在 Linux 服务器上启动一个服务，本机通过 SSH tunnel 访问。

任务：

- build static frontend
- mount static assets in FastAPI
- add CLI command `noviscope serve`
- document SSH tunnel startup
- add `.env.example`

验收：

- server runs on `127.0.0.1:8000`
- user can open `http://127.0.0.1:8000` through SSH tunnel
- refresh browser route works
- `/api` endpoints still work

### Phase 4: Simple Worker Skeleton

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
- pytest for quest/stage transition rules
- pytest for provider key redaction
- pytest for agent assignment behavior

前端：

- TypeScript build must pass
- basic component tests can wait until UI stabilizes
- Playwright smoke test should be added once static serving exists

人工验收：

- create provider
- create quest
- view quest board
- open stage detail
- approve/reject/revise a stage
- confirm API key is never displayed
- confirm SSH tunnel access works

## 13. 非目标

Web MVP 不做：

- 完整论文编辑器
- 复杂图数据库可视化
- WebSocket 实时协作
- 多租户权限系统
- 公开 SaaS 部署
- 自动 GPU 实验运行
- 完整 agent 自动执行
- 完整 shadcn/ui 设计系统

这些能力应在 Web MVP 证明可用之后分阶段实现。

## 14. 风险和缓解

### 风险：Web 页面过早复杂化

缓解：第一版只做 7 个页面，优先使用表格、卡片和可折叠 JSON。

### 风险：用户被模型配置劝退

缓解：默认单模型模式，只要求一个 provider。高级 agent assignment 后置。

### 风险：SQLite 后续迁移成本

缓解：数据库访问继续通过 service 层和 SQLModel 管理，不在前端或业务逻辑里依赖 SQLite 特性。

### 风险：实验运行污染服务环境

缓解：实验 runner 使用独立 working directory，不在 Web MVP 阶段直接执行高风险代码。

### 风险：文档和实现漂移

缓解：Web MVP 每个阶段完成后更新 README 和本设计文档中的状态说明，PR 描述必须引用验收方式。

## 15. 成功标准

Web MVP 成功不是页面完整，而是用户可以完成一条可见的最小科研任务路径：

```text
configure provider
-> create quest
-> inspect demand_validator stage
-> write evidence payload
-> approve/reject stage
-> see quest state change
```

这条路径跑通后，再接入真实文献检索、需求验证 agent、后台 worker 和实验 runner。
