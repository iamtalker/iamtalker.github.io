#!/usr/bin/env python3
"""Runs every book's own build.py (as registered in books.json) against the
shared docs/ tree. This is the one place update.bat needs to call for
content - adding a new book means adding a build.py under tools/books/
plus one entry here in books.json, never a new .bat or a new call site.
"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DOCS = sys.argv[1] if len(sys.argv) > 1 else "docs"

books = json.load(open(os.path.join(REPO_ROOT, "books.json"), encoding="utf-8"))

failed = []
for book in books:
    build_script = os.path.join(REPO_ROOT, book["build"])
    print("=== building %s ===" % book["slug"])
    result = subprocess.run(
        [sys.executable, build_script, OUT_DOCS], cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        failed.append(book["slug"])

if failed:
    print("FAILED: %s" % ", ".join(failed))
    sys.exit(1)
