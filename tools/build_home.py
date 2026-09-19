#!/usr/bin/env python3
"""Regenerates docs/index.md (the home page domain-card grid) from sidebar.json.
Run after build_site.py, which writes sidebar.json but doesn't touch index.md.
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIDEBAR_JSON = os.path.join(REPO_ROOT, "sidebar.json")
INDEX_MD = os.path.join(REPO_ROOT, "docs", "index.md")

sidebar = json.load(open(SIDEBAR_JSON, encoding="utf-8"))

home = """---
layout: home
hero:
  name: "iamtalker"
  text: "존재에서 세계까지"
  tagline: 개인 철학 에세이 — 내면에서 외면으로
---

%s
""" % "\n".join(
    "%d. [%s](/%s/)" % (i, d["text"], d["text"]) for i, d in enumerate(sidebar, 1)
)

with open(INDEX_MD, "w", encoding="utf-8", newline="\n") as f:
    f.write(home)

print("index.md regenerated (%d domains)" % len(sidebar))
