# -*- coding: utf-8 -*-
"""部署 AI 标注小改"""
import sys
import time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from deploy.ssh_run import run

code, out, err = run("cd /opt/hotmailbrief && docker compose build backend 2>&1 | tail -2", timeout=900)
print("build:", out, err[-200:])
code, out, err = run("cd /opt/hotmailbrief && docker compose up -d 2>&1 | tail -2", timeout=600)
print("up:", out)
time.sleep(10)
code, out, err = run("curl -fsS -o /dev/null -w 'HTTPS:%{http_code}' https://mail.muyang-bai.com/", timeout=60)
print("HTTPS:", out)
