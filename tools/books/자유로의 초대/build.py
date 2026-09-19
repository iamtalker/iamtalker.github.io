#!/usr/bin/env python3
"""
Builds this one book ("자유로의 초대") from iamtalker_docs.txt + wordblock/*.txt
into the shared docs/ tree. Every book gets its own folder under
tools/books/<slug>/ with its own build.py like this one, since each book's
source format can be completely different - this one happens to be a
DokuWiki collection, but a future book might come from plain Markdown
files, a different wiki, etc. tools/run_all_books.py (driven by
books.json) is what invokes each book's build.py in turn, so adding a book
never means writing a new update.bat - only a new build.py plus one entry
in books.json.

Reads the DokuWiki master TOC (L1 ====== domain, L2 ===== theme, L3 ====
post title, followed by a {{page>wordblock:ID}} / page>wordblock:ID
reference), resolves each reference against wordblock/<id>.txt, converts
that file's DokuWiki markup to Markdown via pandoc, and writes one .md
file per post, an index.md per domain, this book's own home page, and a
VitePress sidebar config that mirrors the L1/L2/L3 nesting.
"""
import json
import os
import re
import subprocess
import sys

PAGES_DIR = r"C:\MyData\DokuWikiStick\dokuwiki\data\pages"
WORDBLOCK_DIR = os.path.join(PAGES_DIR, "wordblock")
DOCS_TXT = os.path.join(PAGES_DIR, "iamtalker_docs.txt")
OUT_DOCS = sys.argv[1] if len(sys.argv) > 1 else r"docs"
PANDOC = r"C:\Users\misti\AppData\Local\Pandoc\pandoc.exe"

BOOK_SLUG = "자유로의 초대"
BOOK_TAGLINE = "개인 철학 에세이 — 내면에서 외면으로"


def clean_id(raw):
    s = raw.replace(":", "")
    s = s.strip().lower()
    s = s.replace(";", ":").replace("/", "_")
    s = re.sub(r"[^\w:.\-*]", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    s = re.sub(r":+", ":", s)
    s = s.strip(":._-")
    s = re.sub(r":[:._\-]+", ":", s)
    s = re.sub(r"[:._\-]+:", ":", s)
    return s


def slugify_path(title):
    # keep Korean/ascii chars, replace path-unsafe punctuation with '-'
    s = title.strip()
    s = re.sub(r'[\\/:*?"<>|]', "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def md_from_wordblock(post_id):
    path = os.path.join(WORDBLOCK_DIR, post_id + ".txt")
    raw = open(path, encoding="utf-8").read()
    # pandoc's dokuwiki reader treats any {{...}} as a media/image
    # reference (that's core DokuWiki {{image.png}} syntax) - it doesn't
    # know about the `tag` plugin's {{tag>...}}, so {{tag>}} turns into a
    # broken image link ![](tag>) that VitePress then tries to resolve as
    # a file import and fails the build. Strip tag macros (metadata, not
    # content) before conversion.
    raw = re.sub(r"\{\{tag>[^}]*\}\}", "", raw)
    result = subprocess.run(
        [PANDOC, "-f", "dokuwiki", "-t", "gfm"],
        input=raw, capture_output=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError("pandoc failed on %s: %s" % (path, result.stderr))
    md = result.stdout
    # the wordblock file's own ====== header (if any) becomes an H1;
    # drop it since the post title is already the page's VitePress title
    md = re.sub(r"^#\s+.+\n+", "", md, count=1)
    return md.strip()


def write_domain_index(domain_dir, sidebar_domain, prev_domain, next_domain):
    # Plain markdown link syntax ([text](url)) doesn't get parsed inside
    # VitePress content here - it shows up as literal "[text](url)" text
    # on the page instead of a clickable link (same issue the home page
    # hit). Raw HTML <a> tags inside the list items render correctly.
    lines = []
    # VitePress's own auto prev/next (derived from the active sidebar) only
    # works for pages that are themselves listed as a "link" item in that
    # sidebar - a domain's own index.md isn't (only its posts are), so it
    # was showing an inconsistent prev/next (e.g. only "이전 장", no "다음
    # 장"). Set both explicitly here, same as the flat_posts loop below
    # does for posts.
    frontmatter = {}
    if prev_domain:
        frontmatter["prev"] = {"text": "이전 장: %s" % prev_domain[0], "link": prev_domain[1]}
    if next_domain:
        frontmatter["next"] = {"text": "다음 장: %s" % next_domain[0], "link": next_domain[1]}
    lines.append("---")
    lines.append("giscus: false")  # a table of contents isn't a page to comment on
    for key in ("prev", "next"):
        if key in frontmatter:
            lines.append("%s:" % key)
            lines.append("  text: %s" % json.dumps(frontmatter[key]["text"], ensure_ascii=False))
            lines.append("  link: %s" % json.dumps(frontmatter[key]["link"], ensure_ascii=False))
    lines.append("---\n")

    lines.append("# %s\n" % sidebar_domain["text"])

    def walk(items):
        for it in items:
            if "link" in it:
                lines.append('- <a href="%s">%s</a>' % (it["link"], it["text"]))
            else:
                lines.append("\n**%s**\n" % it["text"])
                walk(it["items"])

    walk(sidebar_domain["items"])
    with open(os.path.join(domain_dir, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def write_book_index(out_docs, sidebar):
    # This book's own home page (hero + domain list), same raw-HTML-link
    # fix as write_domain_index (see build bugs in memory/README).
    lines = ['<li><a href="/%s/%s/">%s</a></li>' % (BOOK_SLUG, d["text"], d["text"]) for d in sidebar]
    home = """---
layout: home
hero:
  name: "%s"
  tagline: %s
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
""" % (BOOK_SLUG, BOOK_TAGLINE, "\n".join(lines))

    book_dir = os.path.join(out_docs, BOOK_SLUG)
    os.makedirs(book_dir, exist_ok=True)
    with open(os.path.join(book_dir, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(home)


def main():
    text = open(DOCS_TXT, encoding="utf-8").read()
    lines = text.split("\n")

    domains = []          # [{title, groups: [{title, posts: [{title, id}]}]}]
    cur_domain = cur_group = None

    for line in lines:
        m1 = re.match(r"^======\s*(.+?)\s*======\s*$", line)
        if m1:
            cur_domain = {"title": m1.group(1).strip(), "groups": []}
            domains.append(cur_domain)
            cur_group = None
            continue
        m2 = re.match(r"^=====\s*(.+?)\s*=====\s*$", line)
        if m2:
            cur_group = {"title": m2.group(1).strip(), "posts": []}
            cur_domain["groups"].append(cur_group)
            continue
        m3 = re.match(r"^====\s*(.+?)\s*====\s*$", line)
        if m3:
            post_title = m3.group(1).strip()
            target = cur_group if cur_group is not None else None
            if target is None:
                # domain with posts directly under it, no L2 group yet
                cur_group = {"title": None, "posts": []}
                cur_domain["groups"].append(cur_group)
                target = cur_group
            target["posts"].append({"title": post_title, "refs": []})
            continue
        mref = re.search(r"page>wordblock:([^&\n}]+)(&[^\n}]*)?", line)
        if mref and cur_domain and cur_domain["groups"]:
            last_group = cur_domain["groups"][-1]
            if last_group["posts"]:
                last_group["posts"][-1]["refs"].append(mref.group(1).strip())

    total_posts = sum(len(g["posts"]) for d in domains for g in d["groups"])
    print("[%s] domains=%d groups=%d posts=%d" % (
        BOOK_SLUG, len(domains), sum(len(d["groups"]) for d in domains), total_posts))

    os.makedirs(OUT_DOCS, exist_ok=True)
    sidebar = []
    missing_content = []
    flat_posts = []  # [{file_path, title, link, domain_title}] in reading order

    def domain_link(d):
        return "/%s/%s/" % (BOOK_SLUG, slugify_path(d["title"]))

    for domain_idx, domain in enumerate(domains):
        domain_slug = slugify_path(domain["title"])
        domain_dir = os.path.join(OUT_DOCS, BOOK_SLUG, domain_slug)
        os.makedirs(domain_dir, exist_ok=True)
        sidebar_domain = {"text": domain["title"], "items": []}

        for group in domain["groups"]:
            group_items = []
            for post in group["posts"]:
                if not post["refs"]:
                    missing_content.append(post["title"])
                    continue
                post_id = clean_id(post["refs"][0])
                try:
                    body = md_from_wordblock(post_id)
                except Exception as e:
                    missing_content.append("%s (%s): %s" % (post["title"], post_id, e))
                    continue
                post_slug = slugify_path(post["title"])
                file_path = os.path.join(domain_dir, post_slug + ".md")
                with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write("# %s\n\n%s\n" % (post["title"], body))
                link = "/%s/%s/%s" % (BOOK_SLUG, domain_slug, post_slug)
                group_items.append({"text": post["title"], "link": link})
                flat_posts.append({
                    "file_path": file_path, "title": post["title"],
                    "link": link, "domain_title": domain["title"],
                })

            if group["title"] is None:
                sidebar_domain["items"].extend(group_items)
            else:
                sidebar_domain["items"].append({
                    "text": group["title"], "collapsed": False, "items": group_items,
                })

        sidebar.append(sidebar_domain)
        prev_domain = (domains[domain_idx - 1]["title"], domain_link(domains[domain_idx - 1])) if domain_idx > 0 else None
        next_domain = (domains[domain_idx + 1]["title"], domain_link(domains[domain_idx + 1])) if domain_idx < len(domains) - 1 else None
        write_domain_index(domain_dir, sidebar_domain, prev_domain, next_domain)

    # prev/next footer links, chained across the whole book in reading
    # order - crossing from the last post of one domain straight into the
    # first post of the next (rather than dead-ending at the end of each
    # domain, which is what VitePress's own sidebar-scoped prev/next does,
    # since each domain has its own separate sidebar config).
    for i, post in enumerate(flat_posts):
        frontmatter = {}
        if i > 0:
            prev = flat_posts[i - 1]
            label = prev["title"]
            if prev["domain_title"] != post["domain_title"]:
                label = "이전 장: %s" % prev["domain_title"]
            frontmatter["prev"] = {"text": label, "link": prev["link"]}
        if i < len(flat_posts) - 1:
            nxt = flat_posts[i + 1]
            label = nxt["title"]
            if nxt["domain_title"] != post["domain_title"]:
                label = "다음 장: %s" % nxt["domain_title"]
            frontmatter["next"] = {"text": label, "link": nxt["link"]}

        body = open(post["file_path"], encoding="utf-8").read()
        fm_lines = ["---"]
        for key in ("prev", "next"):
            if key in frontmatter:
                fm_lines.append("%s:" % key)
                fm_lines.append("  text: %s" % json.dumps(frontmatter[key]["text"], ensure_ascii=False))
                fm_lines.append("  link: %s" % json.dumps(frontmatter[key]["link"], ensure_ascii=False))
        fm_lines.append("---\n")
        with open(post["file_path"], "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(fm_lines) + "\n" + body)

    write_book_index(OUT_DOCS, sidebar)

    # NOTE: sidebar.json currently lives at the repo root and .vitepress/
    # config.mjs reads just this one file - fine while there's only one
    # book with content. When a second book gets its own build.py, this
    # should become e.g. docs/<BOOK_SLUG>/.sidebar.json per book, and
    # config.mjs updated to merge all of them. Not done yet since there's
    # nothing to merge with.
    with open(os.path.join(os.path.dirname(OUT_DOCS) or ".", "sidebar.json"),
              "w", encoding="utf-8") as f:
        json.dump(sidebar, f, ensure_ascii=False, indent=2)

    print("[%s] missing content (%d):" % (BOOK_SLUG, len(missing_content)))
    for m in missing_content:
        print(" -", m)


if __name__ == "__main__":
    main()
