"""验证码邮件（t110 · M4）

与思忆 AiLifeOS 的 server/smtp.mjs 使用同一版式，只换品牌名：
品牌头 + 主色细条、32px 等宽验证码（浅蓝底圆角框）、有效期与用途、非本人可忽略、页脚备案号。
遵守 QQ 邮箱约束：纯 div、样式内联、无 table、无图片、页脚不放链接按钮。
"""

from __future__ import annotations

import html as _html

from app.utils.compliance import ICP_RECORD

BRAND = "一勺热点"
BRAND_EN = "SpoonBrief"


def verification_subject(code: str) -> str:
    return f"{BRAND}验证码：{code}"


def render_verification_email(code: str, purpose: str = "登录、注册或重置密码") -> str:
    c = _html.escape(str(code))
    return f"""<div style="margin:0;padding:24px 12px;background:#F5F7FB;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="max-width:480px;margin:0 auto;background:#ffffff;border:1px solid #E6EAF2;border-radius:16px;overflow:hidden;">
    <div style="height:4px;background:#5B7CFF;"></div>
    <div style="padding:22px 22px 6px;">
      <div style="font-size:15px;font-weight:700;color:#1F2937;letter-spacing:0.5px;">{BRAND} <span style="color:#8A94A6;font-weight:600;">{BRAND_EN}</span></div>
      <div style="margin-top:18px;font-size:16px;color:#374151;">你的验证码</div>
      <div style="margin-top:10px;background:#F0F3FF;border-radius:12px;padding:16px 8px;text-align:center;font-family:'SFMono-Regular',Menlo,Consolas,'Liberation Mono','Courier New',monospace;font-size:32px;font-weight:700;letter-spacing:6px;color:#1F2A5A;">{c}</div>
      <div style="margin-top:16px;font-size:15px;color:#4B5563;line-height:1.75;">5 分钟内有效，只用于{_html.escape(purpose)}。</div>
      <div style="font-size:15px;color:#4B5563;line-height:1.75;">如果不是你本人操作，忽略这封邮件即可。请不要把验证码告诉任何人。</div>
    </div>
    <div style="margin-top:18px;padding:12px 22px 14px;border-top:1px solid #EEF1F6;font-size:12px;color:#9AA3B2;line-height:1.75;">{BRAND} {BRAND_EN} · 与思忆 AiLifeOS 共用账号<br>隐私政策见网站页脚 · {ICP_RECORD}</div>
  </div>
</div>"""
