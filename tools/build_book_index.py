#!/usr/bin/env python3
"""Regenerates docs/<BOOK_SLUG>/index.md (this book's own domain-list page)
from sidebar.json. Run after build_site.py, which writes sidebar.json but
doesn't touch this file. Replaces the old build_home.py now that the book
lives under its own path instead of the site root (see build_library.py
for the new root page).
"""
import json
import os

BOOK_SLUG = "자유로의 초대"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIDEBAR_JSON = os.path.join(REPO_ROOT, "sidebar.json")
INDEX_MD = os.path.join(REPO_ROOT, "docs", BOOK_SLUG, "index.md")

sidebar = json.load(open(SIDEBAR_JSON, encoding="utf-8"))

home = """---
layout: home
hero:
  name: "%s"
  tagline: 개인 철학 에세이 — 내면에서 외면으로
---

<ol class="domain-order">
%s
</ol>

<style>
.domain-order {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 24px;
  font-size: 18px;
  line-height: 2.4;
}
.domain-order a {
  color: var(--vp-c-text-1);
  text-decoration: none;
}
.domain-order a:hover {
  color: var(--vp-c-brand-1);
  text-decoration: underline;
}
</style>
""" % (
    BOOK_SLUG,
    "\n".join(
        '<li><a href="/%s/%s/">%s</a></li>' % (BOOK_SLUG, d["text"], d["text"])
        for d in sidebar
    ),
)

os.makedirs(os.path.dirname(INDEX_MD), exist_ok=True)
with open(INDEX_MD, "w", encoding="utf-8", newline="\n") as f:
    f.write(home)

print("%s/index.md regenerated (%d domains)" % (BOOK_SLUG, len(sidebar)))
