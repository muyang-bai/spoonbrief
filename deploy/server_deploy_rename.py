# -*- coding: utf-8 -*-
"""部署品牌改名到服务器"""
import sys
import time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from deploy.ssh_run import run

# 1. PG 合规文本改名
code, out, err = run(
    "cd /opt/hotmailbrief && docker compose exec -T postgres psql -U hotmail -d hotmailbrief -c "
    "\"UPDATE compliance_texts SET content = replace(replace(content, 'HotMail Brief', '一勺热点'), 'HotMail', '一勺热点') WHERE content LIKE '%HotMail%'\"",
    timeout=300,
)
print("PG 合规文本:", out[-200:], err[-200:])

# 2. 重建 + 重启
code, out, err = run("cd /opt/hotmailbrief && docker compose build backend 2>&1 | tail -2", timeout=900)
print("build:", out, err[-200:])
code, out, err = run("cd /opt/hotmailbrief && docker compose up -d 2>&1 | tail -3", timeout=600)
print("up:", out)
time.sleep(12)

# 3. 验证：健康 + 邮件模板品牌 + favicon
code, out, err = run(
    "curl -fsS -o /dev/null -w 'HTTPS:%{http_code}\n' https://mail.muyang-bai.com/; "
    "curl -fsS https://mail.muyang-bai.com/favicon.svg | head -c 120; echo ''; "
    "curl -fsS https://mail.muyang-bai.com/logo-512.png -o /dev/null -w 'logo:%{http_code}\n'",
    timeout=120,
)
print(out)

code, out, err = run(
    "cd /opt/hotmailbrief && docker compose exec -T backend python -c \""
    "from app.services.email_template import render_email; "
    "h = render_email('测试','2026-09-12','近 7 天','<p>x</p>',[],[],'','','',''); "
    "print('邮件含一勺热点:', '一勺热点' in h); print('邮件含HotMail:', 'HotMail' in h)\"",
    timeout=300,
)
print(out)
