"""AI 用量记账：把每次 LLM 调用的 token 消耗落库，供后台用量看板统计。

上下文（用户 / 订阅 / 报告 / 阶段）由调用方通过 set_usage_context 注入，
_call_llm 拿到模型返回的 usage 后自动记账，业务代码无需改动。
"""
from __future__ import annotations

import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)

usage_ctx: ContextVar[dict] = ContextVar("usage_ctx", default={})

# 默认单价（元 / 百万 token），可在 system_config 表用
# token_price_input / token_price_output 覆盖；仅用于预估展示
DEFAULT_PRICE_INPUT = 1.0
DEFAULT_PRICE_OUTPUT = 3.0


def set_usage_context(**kwargs) -> None:
    """设置当前任务的记账上下文（user_id / subscription_id / report_id / stage）"""
    ctx = dict(usage_ctx.get() or {})
    ctx.update({k: v for k, v in kwargs.items() if v is not None})
    usage_ctx.set(ctx)


def clear_usage_context() -> None:
    usage_ctx.set({})


def get_prices(db) -> tuple[float, float]:
    """单价（元/百万 token）：优先读系统配置，缺省用默认值"""
    try:
        from app.models.system_config import SystemConfig

        rows = db.query(SystemConfig).filter(
            SystemConfig.key.in_(["token_price_input", "token_price_output"])
        ).all()
        cfg = {r.key: r.value for r in rows}
        pin = float(cfg.get("token_price_input") or DEFAULT_PRICE_INPUT)
        pout = float(cfg.get("token_price_output") or DEFAULT_PRICE_OUTPUT)
        return pin, pout
    except Exception:
        return DEFAULT_PRICE_INPUT, DEFAULT_PRICE_OUTPUT


def record_usage(usage, model: str, stage: str | None = None) -> None:
    """把一次 LLM 调用的用量落库；任何异常都不影响主流程"""
    if usage is None:
        return
    try:
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        if prompt_tokens == 0 and completion_tokens == 0:
            return

        ctx = usage_ctx.get() or {}
        from app.database import SessionLocal
        from app.models.token_usage import TokenUsage

        db = SessionLocal()
        try:
            price_in, price_out = get_prices(db)
            cost = prompt_tokens / 1_000_000 * price_in + completion_tokens / 1_000_000 * price_out
            db.add(TokenUsage(
                user_id=ctx.get("user_id"),
                subscription_id=ctx.get("subscription_id"),
                report_id=ctx.get("report_id"),
                model=model,
                stage=stage or ctx.get("stage") or "analyze",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_yuan=round(cost, 6),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:  # 记账失败绝不影响生成
        logger.warning(f"用量记账失败: {e}")
