# 一勺热点（SpoonBrief）

> 全网热点，AI 分析后，喂到你嘴边。

一勺热点是一个 **AI 驱动的热点情报简报工具**：每天自动扫描全网热点，结合你的身份与关注方向，把热点翻译成**机会、风险与行动建议**，定时送到邮箱。

**核心主张：每天一封，只讲与你有关、且这次真的新增了什么。**

- 在线体验：<https://mail.muyang-bai.com>（演示账号 `demo@muyang-bai.com` / `spoonbrief2026`）
- AI 分析由 DeepSeek 生成 · 内容仅供参考，不构成投资建议
- 本项目为 iCAN 大学生创新创业大赛（AI 产品实现方向）参赛作品，团队：一勺热点队

---

## 为什么做这个

每天 700+ 条热点，90% 与你无关；刷 40 分钟，记住的只有焦虑。通用 AI 新闻工具有两个通病：
**结论不可溯源** 与 **每天把同一批新闻重新总结一遍**（看起来是新的，其实没有新增信息）。

一勺热点的回答：

| 问题 | 做法 |
|---|---|
| 信息过载 | 语义归并去重，同一事件多源报道合并为一条 |
| 与你无关 | 订阅方向 + 用户画像 + 关键词分词匹配，AI 按你的视角解读 |
| 每天重复 | **事件级跨期记忆**：同事件换标题/转载/AI 重述都判为重复；只有出现「新来源 + 新日期或新数据」才算进展 |
| 没有更新 | 用户可选：跳过本次 / 改为周期汇总 / 照常推送 |
| 结论不可信 | 每条素材附原文链接与五星信源等级（按来源类型，附评级依据） |
| 反馈没用 | 邮件「有用 / 没用 + 原因」回流，下一期生成时作为约束注入 |

---

## 功能一览（v2）

- **订阅与调度**：方向关键词、时间窗、cron 频率、分析模板、无更新策略
- **信息池**：19 个信源每 30 分钟抓取，指纹去重 + 可信度打分 + 事件聚合
- **事件级新颖性**：别名实体链接 + SimHash + 相似度聚类，输出 `fresh / progress / repeat`
- **AI 分析**：6 套分析师模板（默认 / 投资 / 创业 / 行业深度 / 竞品 / 每日精读），单次调用产出全文
- **决策层**：一句话结论、30 秒速览、情绪（利好/利空/中性）、影响分 1–10、今日行动清单、五维影响
- **邮件简报**：浅色蓝版式、图文结构、原文链接、五星信源、事件进展（上次→这次）、周期汇总版式
- **反馈闭环**：有用/没用 + 5 类原因（方向/太浅/太旧重复/依据不足/太长）
- **画像**：8 维画像 + 完成度 + 「AI 实际看到的画像」透明预览
- **管理端**：用户、模板、信源、公告、SMTP、AI 配置、用量看板（消费/请求/Tokens/模型分布/去重效率）
- **双产品联动**：与 AiLifeOS 共库、HMAC 互通、同邮箱自动绑定，简报同步到 App

---

## 技术栈

- 后端：Python 3.11 + FastAPI + SQLAlchemy + Celery 5
- 前端：Vue 3 + Vite
- 数据：MySQL 8（与 AiLifeOS 共用库，热点表 `hb_` 前缀）、Redis 7（队列 + 30s 响应缓存）
- 模型：DeepSeek（deepseek-flash）
- 部署：Docker Compose（backend / frontend / worker / beat / redis）+ nginx + Let's Encrypt

---

## 快速开始

```bash
# 1. 配置环境变量（不要提交真实密钥）
cp backend/.env.example backend/.env
#    至少填写：DATABASE_URL / REDIS / SECRET_KEY / ENCRYPTION_KEY / DEEPSEEK_API_KEY / SMTP_*

# 2. 启动
docker compose up -d --build

# 3. 打开
#   http://localhost:8080       前端
#   http://localhost:8000/docs  API 文档
```

生产部署使用三份 compose 叠加（固定镜像版本，便于回滚）：

```bash
docker compose -f docker-compose.yml \
               -f docker-compose.frontend-image.yml \
               -f docker-compose.t158-credits.yml up -d
```

---

## 目录结构

```
backend/
  app/
    api/         # 用户端 / 管理端 / 内部互通接口
    models/      # SQLAlchemy 模型（含事件记忆 story_memory）
    services/    # 抓取、去重、新颖性、分析、决策、渲染、发送、用量
    tasks/       # Celery 任务：调度、报告生成、邮件
    utils/       # 加密、合规、安全抓取
frontend/
  src/views/     # 用户台 + 管理台
  src/components/
docs/            # 说明书、架构图、参赛材料
```

关键文件：
- `backend/app/services/novelty.py` — 事件级去重与进展判定
- `backend/app/services/entity_link.py` — 别名实体链接 + SimHash
- `backend/app/services/decision_layer.py` — 结构化决策层
- `backend/app/services/email_template.py` — 邮件版式
- `backend/app/tasks/report_tasks.py` — 端到端报告流水线

---

## 文档

- `docs/参赛材料/产品说明书_v2.md` — 产品逻辑链路、架构、数据、商业化
- `docs/参赛材料/大赛_架构图与流程图.md` — 6 张 Mermaid（架构/链路/新颖性/反馈/双产品/调度）
- `docs/参赛材料/产品评估与优化路线.md` — 现状评估与排期

---

## 合规

- AI 内容标注：AI 辅助分析，不是来源原文或已核实结论
- 五星信源仅表示来源类型可溯性，不代表真实性概率
- 不构成投资建议；每封邮件独立退订令牌，退订即时生效

## License

MIT
