#!/usr/bin/env python3
"""Regenerates docs/index.md - the site root, a "library" page listing every
book (each book being one /<slug>/ tree built by its own converter script,
e.g. build_site.py for 자유로의 초대). Add a new book by adding an entry to
books.json and giving it its own build script; this file just lists them.
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKS_JSON = os.path.join(REPO_ROOT, "books.json")
INDEX_MD = os.path.join(REPO_ROOT, "docs", "index.md")

books = json.load(open(BOOKS_JSON, encoding="utf-8"))

home = """---
layout: home
hero:
  name: "iamtalker"
  tagline: 글 모음
---

<ol class="book-shelf">
%s
</ol>

<style>
.book-shelf {
  max-width: 640px;
  margin: 0 auto;
  padding: 0 24px;
  font-size: 20px;
  line-height: 2.6;
}
.book-shelf a {
  color: var(--vp-c-text-1);
  font-weight: 600;
  text-decoration: none;
}
.book-shelf a:hover {
  color: var(--vp-c-brand-1);
  text-decoration: underline;
}
.book-shelf .tagline {
  display: block;
  font-size: 14px;
  font-weight: 400;
  color: var(--vp-c-text-2);
}
</style>
""" % "\n".join(
    '<li><a href="/%s/">%s</a><span class="tagline">%s</span></li>'
    % (b["slug"], b["slug"], b["tagline"])
    for b in books
)

with open(INDEX_MD, "w", encoding="utf-8", newline="\n") as f:
    f.write(home)

print("docs/index.md (library) regenerated (%d books)" % len(books))
