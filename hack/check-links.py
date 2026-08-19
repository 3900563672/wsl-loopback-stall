#!/usr/bin/env python3
"""检查 docs/archive/README 内相对 Markdown 链接与反引号路径引用是否存在。"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CODE_RE = re.compile(r"`([^`]+\.md)`")
SKIP = ("http://", "https://", "#", "mailto:", "gh ")

errors = 0
for p in [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md")), ROOT / "archive" / "README.md"]:
    text = p.read_text(encoding="utf-8")
    for m in LINK_RE.findall(text) + CODE_RE.findall(text):
        target = m.split("#")[0].strip()
        if not target or target.startswith(SKIP) or target.startswith(("早期", "上游")):
            continue
        cand = (p.parent / target).resolve()
        if not cand.exists():
            print(f"BROKEN: {p.relative_to(ROOT)} -> {target}")
            errors += 1
sys.exit(1 if errors else 0)
