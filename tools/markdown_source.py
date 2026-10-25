"""Markdown folder -> the book-file text that build_books.py already parses.

Layout of the markdown source folder (markdown_dir in config.json):

  markdown_dir/
    My Book/                 <- one sub-folder = one book
      01 Chapter/            <- folder   = 대분류 (chapter)
        Topic/               <- folder   = 소주제 (group, optional)
          Essay.md           <- file     = 글 (post)
        Standalone.md        <- a file may sit directly in a chapter
      Intro.md               <- a file may sit directly in the book
    Single Page.md           <- a loose .md file = a one-page book

Folders deeper than that are flattened: their files become posts titled
"folder - file". A leading "01 " / "02_" in a name only sets the order and is
dropped from the title. The synthesized text uses DokuWiki heading syntax with
each file's markdown wrapped in <markdown>...</markdown>, which the existing
pipeline already passes through untouched, so both sources share one builder.
"""
import os
import re
import shutil
import urllib.parse

NUM_PREFIX_RE = re.compile(r"^\d+[\s._)\-]+")
FRONT_RE = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.MULTILINE)
MD_IMG_RE = re.compile(r'(!\[[^\]]*\]\()(<[^>]+>|[^)\s]+)((?:\s+"[^"]*")?\))')
OBS_IMG_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def natural_key(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def clean_title(name):
    s = os.path.splitext(name)[0] if name.lower().endswith(".md") else name
    s = NUM_PREFIX_RE.sub("", s).strip()
    s = s.replace("=", "-")  # "=" would be read as a DokuWiki header marker
    return s or name


def _entries(path):
    out = []
    for name in sorted(os.listdir(path), key=natural_key):
        if name.startswith(".") or name.startswith("_"):
            continue
        full = os.path.join(path, name)
        if os.path.isdir(full) or name.lower().endswith(".md"):
            out.append((name, full))
    return out


class _Images:
    """Copies images a note references into docs/public/<book>/ and rewrites
    the link to the root-relative URL the site will serve it at."""

    def __init__(self, book_slug, book_root, public_dir):
        self.slug = book_slug
        self.root = book_root
        self.public = public_dir
        self.by_name = {}
        for r, _dirs, files in os.walk(book_root):
            for f in files:
                if f.lower().endswith(IMAGE_EXTS):
                    self.by_name.setdefault(f.lower(), os.path.join(r, f))

    def _publish(self, src):
        rel = os.path.relpath(src, self.root).replace(os.sep, "/")
        dest = os.path.join(self.public, self.slug, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        return "/" + urllib.parse.quote("%s/%s" % (self.slug, rel))

    def rewrite(self, md, md_path):
        base = os.path.dirname(md_path)

        def obsidian(m):
            name = m.group(1).strip()
            src = os.path.join(base, name)
            if not os.path.exists(src):
                src = self.by_name.get(os.path.basename(name).lower())
            if not src or not os.path.exists(src):
                return ""
            return "![%s](%s)" % (os.path.basename(name), self._publish(src))

        def standard(m):
            target = m.group(2).strip("<>")
            if re.match(r"^(https?:|data:|/)", target):
                return m.group(0)
            local = urllib.parse.unquote(target.split("#", 1)[0].split("?", 1)[0])
            src = os.path.normpath(os.path.join(base, local))
            if not os.path.isfile(src):
                src = self.by_name.get(os.path.basename(local).lower())
            if not src:
                return m.group(0)
            return m.group(1) + self._publish(src) + m.group(3)

        md = OBS_IMG_RE.sub(obsidian, md)
        return MD_IMG_RE.sub(standard, md)


def _read_note(path):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    title = None
    m = FRONT_RE.match(text)
    if m:
        t = TITLE_RE.search(m.group(1))
        if t:
            title = t.group(1).strip("\"'")
        text = text[m.end():]
    return title, text.strip()


def _header(level, title):
    eq = "=" * level
    return "%s %s %s" % (eq, title, eq)


def _note_block(level, title, path, images):
    fm_title, body = _read_note(path)
    body = images.rewrite(body, path)
    return "%s\n<markdown>\n%s\n</markdown>\n" % (_header(level, fm_title or title), body)


def _emit(path, depth, images, prefix=""):
    """DokuWiki-style text for every note under `path`. Depth 0/1/2 map to
    heading levels 6/5/4 (chapter / group / post); anything deeper flattens."""
    out = []
    level = max(4, 6 - depth)
    for name, full in _entries(path):
        title = clean_title(name)
        if os.path.isdir(full):
            if depth < 2:
                inner = _emit(full, depth + 1, images)
                if inner.strip():
                    out.append(_header(level, title) + "\n\n" + inner)
            else:
                out.append(_emit(full, depth, images, prefix + title + " - "))
        else:
            out.append(_note_block(level, prefix + title, full, images))
    return "\n".join(out)


def collect_books(markdown_dir, public_dir):
    """[(book_slug, book_text)] for every book under markdown_dir."""
    books = []
    for name, full in _entries(markdown_dir):
        slug = clean_title(name)
        if os.path.isdir(full):
            images = _Images(slug, full, public_dir)
            text = _emit(full, 0, images)
        else:
            images = _Images(slug, os.path.dirname(full), public_dir)
            text = _note_block(6, slug, full, images)
        if text.strip():
            books.append((slug, text))
    return books
