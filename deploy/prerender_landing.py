# -*- coding: utf-8 -*-
"""
落地页预渲染（本地工具，前端内容变更后重新运行）
- 用真实浏览器渲染 http://127.0.0.1:3001（先执行 build_frontend.ps1）
- 滚动触发全部 reveal 动画与演示台就位
- 序列化完整 DOM 到 prerendered/landing.html（供 serve_frontend.py 按爬虫 UA 提供）
用法:  backend\\venv\\Scripts\\python.exe deploy\\prerender_landing.py
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "prerendered")
URL = os.environ.get("PRERENDER_URL", "http://127.0.0.1:3001/")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)

        # 滚动整页：触发 IntersectionObserver reveal、count-up、时间轴
        page.evaluate(
            "async () => { "
            "const h = document.body.scrollHeight; "
            "for (let y = 0; y <= h; y += 500) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } "
            "window.scrollTo(0, 0); }"
        )
        page.wait_for_timeout(1500)

        # 给打字机行补静态内容（爬虫无需动画，但要关键词）
        page.evaluate(
            "() => { const el = document.querySelector('.typed'); if (el && !el.textContent.trim()) el.textContent = '半导体 国产替代'; }"
        )
        # 展开证据链（让"溯源可信"卖点的正文进入 HTML）
        try:
            page.locator(".proof-conclusion").click(timeout=2000)
            page.wait_for_timeout(400)
        except Exception:
            pass

        html = page.evaluate("() => document.documentElement.outerHTML")
        browser.close()

    # 后处理：标记生成信息，移除动画闪烁相关 class（静态页不需要 reveal 隐藏态）
    html = html.replace("<html ", '<!-- prerendered by deploy/prerender_landing.py -->\n<html ', 1)
    html = re.sub(r'class="([^"]*)\breveal\b([^"]*)"', r'class="\1visible\2"', html)

    out_path = os.path.join(OUT_DIR, "landing.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 预渲染完成: {out_path} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
