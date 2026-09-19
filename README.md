# 一勺热点（SpoonBrief）

> 全网热点，AI 分析后，喂到你嘴边。

**一勺热点**是一个 AI 驱动的热点情报简报工具：每天自动扫描全网热点，用大模型结合你的身份与兴趣，
把热点翻译成**机会、风险与行动建议**，定时送到你的邮箱——不用刷，张嘴就行。

- 在线体验：https://mail.muyang-bai.com
- 一句话原理：14 个信源 → 语义归并信息池 → AI 两阶段分析 → 每条结论可溯源 → 每天 08:00 送达邮箱
- AI 分析由 DeepSeek 生成 · 内容仅供参考，不构成投资建议
- 本项目为 iCAN 大学生创新创业大赛（AI 产品实现方向）参赛作品，队伍：一勺热点队

---

## 为什么做这个

每天 700+ 条热点，90% 与你无关；刷 40 分钟，记住的只有焦虑。普通 AI 新闻工具还有两个致命伤：
**结论不可溯源**（AI 说错了无处可查）和**千人一面**（不看你的身份和兴趣）。

一勺热点的回答：

| 问题 | 我们的解法 |
|------|-----------|
| 信息过载 | 语义归并去重，同事件多源报道合并为一条 |
| 与你无关 | 订阅方向 + 用户画像 + 关键词分词级匹配，AI 全局分析师按你的视角解读 |
| AI 不可信 | 每条结论绑定 `[N]` 引用 → 原文链接；多源交叉验证才打可信标；信源按媒体类型分级打分 |
| 没时间看 | 每天 08:00 定时送达邮箱，3 分钟读完，机会/风险/行动建议直接可用 |

---

## 核心功能

- **订阅方向**：选 1–3 个关心方向（如 AI 芯片、低空经济），可自定义关键词与 RSS 信源
- **AI 两阶段分析**：Stage 1 逐条抽取结构化要点（max_tokens 4000）→ Stage 2 注入画像与关键词做全局分析（max_tokens 8000），输出机会/风险/行动建议
- **溯源可信**：正文引用 `[N]` 与原始新闻一一对应，点击即达原文；展示「可信度 X/10 · N 源交叉验证」
- **定时送达**：每天 08:00 准时躺在邮箱；额度透明（默认 60 份/月，可封顶）
- **历史简报**：网页端可回看所有简报与证据链
- **自定义信源**：支持添加你自己的 RSS 源（实验性）

---

## AI 原理（详见 `docs/大赛_架构图与流程图.md` 图 3）

```
候选新闻 ≤12 条（标题带 [N] 编号）
  → Stage 1 信息抽取（DeepSeek，结构化要点）
  → Stage 2 全局分析（注入用户画像+关键词 → 机会/风险/行动建议）
  → 引用链接化（[N] → 原文超链接）
  → 输出清洗（HTML 净化 + 内联样式）
  → 落库 + 邮件模板渲染
```

**语义归并**：同事件三级判定——15 字指纹一致 / jieba 词交集 ≥2 / 2-gram Dice ≥0.40，逐级通过即合并。
**可信度体系**：信源分级（官方 10 / 权威 9 / 专业 7 / 科技 6 / 社区 4）× 独立信源数（≥2 家交叉验证）。

---

## 系统架构

六个 Docker 容器：

```
Nginx(HTTPS) → Frontend(Vue3 SPA) → Backend(FastAPI × Gunicorn)
                                        ├─ PostgreSQL 16（业务数据，每日备份）
                                        └─ Redis 7 ← Celery Beat（每 60s 巡检到期订阅）
                                              └─ Celery Worker → DeepSeek / QQ邮箱 SMTP
```

**可靠性四层防重**：10 分钟去重 → 运行中跳过 → 24h 过期滚动 → TaskRun 落库审计；
watchdog 每 15 分钟自愈孤儿任务；统一扣费（每份简报 1 额度，订阅级 monthly_quota 超支自动跳过并邮件通知）。

完整五张架构图（Mermaid 源码，可直接在 mermaid.live 渲染）见 `docs/大赛_架构图与流程图.md`。

---

## 目录结构

```
├── backend/               # FastAPI + SQLAlchemy + Celery
│   ├── app/api/           # 认证/订阅/报告/信源/退订/管理端
│   ├── app/models/        # 19 张业务表
│   ├── app/services/      # 信息池/语义归并/可信度/AI 分析/邮件
│   ├── app/tasks/         # celery beat + worker 任务
│   └── app/prompts/       # 三套提示词模板（抽取/全局分析/个性化）
├── frontend/              # Vue 3 + Vite 单页应用（12 个页面）
├── deploy/                # 部署脚本与 nginx 配置
├── docs/                  # 产品说明书 / 技术与原理 / 架构图 / 用户反馈清单
└── docker-compose.yml     # 六服务编排
```

---

## 本地开发

### 后端（默认 SQLite，零配置起步）

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 填写 SECRET_KEY / DEEPSEEK_API_KEY / SMTP 等
uvicorn app.main:app --reload --port 8000
```

本地无需 Redis/Celery：`enable_local_scheduler=true`（.env.example 默认开启）会用 APScheduler
在进程内跑巡检、看门狗与信息池抓取。

### 前端

```bash
cd frontend
npm install
npm run dev                 # Vite dev server，/api 代理到 8000
```

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `SECRET_KEY` | 会话/令牌签名密钥（必填） |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥，两阶段分析调用 |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | 简报邮件发送（QQ 邮箱 465 端口可用） |
| `DATABASE_URL` | 默认 `sqlite:///./spoonbrief.db`，生产用 PostgreSQL |
| `ENABLE_LOCAL_SCHEDULER` | true = 本地 APScheduler（开发）；false = Celery beat（生产） |
| `MONTHLY_QUOTA_DEFAULT` | 新用户每月简报额度，默认 60 |

完整清单见 `backend/.env.example`。

---

## 生产部署

```bash
docker compose up -d --build
```

六服务：`nginx` / `frontend` / `backend` / `postgres` / `redis` / `celery-worker`（+ beat 由
celery-worker 内 APScheduler 或独立 beat 服务承载）。数据库每日 03:00 自动备份，详见
`docs/项目说明书_技术与原理.md` 与 `deploy/deploy.sh`。

---

## API 摘要

| 模块 | 端点（节选） |
|------|-------------|
| 认证 | `POST /api/auth/register` `POST /api/auth/login` `POST /api/auth/send-reset-code` `POST /api/auth/reset-password` |
| 订阅 | `GET/POST /api/subscriptions` `POST /api/subscriptions/generate-now` |
| 报告 | `GET /api/reports` `GET /api/reports/{id}`（含证据链） |
| 信源 | `GET/POST /api/sources`（含自定义 RSS） |
| 提示词 | `GET/POST /api/user-prompts`（导出 `.spoonskill.json` 技能包） |
| 退订 | `GET /api/unsubscribe/{token}`（一键退订，合规） |
| 管理 | `/api/admin/*`（用户/额度/信源/SMTP/合规文案/公告，仅管理员） |

接口文档见各 `backend/app/api/*.py` 与前端 `frontend/src/api.js`。

---

## 文档

| 文件 | 内容 |
|------|------|
| `docs/大赛_产品说明书.md` | 参赛产品说明书（痛点/方案/功能/价值/商业模式） |
| `docs/大赛_架构图与流程图.md` | 五张 Mermaid 架构图源码 + 答辩口述文字版 |
| `docs/项目说明书_技术与原理.md` | 技术栈、AI 流水线、可信度模型、调度可靠性细节 |
| `docs/产品优化清单_用户反馈.md` | 真实用户测试反馈与逐项修复记录 |
| `docs/模板创建指南.md` | 提示词模板自定义指南（`.spoonskill.json`） |

---

## 参赛材料包

iCAN 大学生创新创业大赛 · AI 产品实现方向（一勺热点队）

1. 产品说明书（`docs/大赛_产品说明书.md`）
2. 架构图与流程图 ×5（`docs/大赛_架构图与流程图.md`，mermaid.live 导出 PNG 即可）
3. 60 秒产品宣传片（见 `docs/大赛_产品说明书.md` 附录说明）
4. 在线产品：https://mail.muyang-bai.com
5. 本仓库源码

---

## License

[MIT](./LICENSE) © 2026 一勺热点队。AI 输出仅供参考，不构成投资建议。
