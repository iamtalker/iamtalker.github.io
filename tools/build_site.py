#!/usr/bin/env python3
"""
Builds a VitePress `docs/` tree from iamtalker_docs.txt + wordblock/*.txt.

Reads the DokuWiki master TOC (L1 ====== domain, L2 ===== theme, L3 ====
post title, followed by a {{page>wordblock:ID}} / page>wordblock:ID
reference), resolves each reference against wordblock/<id>.txt, converts
that file's DokuWiki markup to Markdown via pandoc, and writes one .md
file per post plus a VitePress sidebar config that mirrors the L1/L2/L3
nesting.
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


def write_domain_index(domain_dir, sidebar_domain):
    # Plain markdown link syntax ([text](url)) doesn't get parsed inside
    # VitePress content here - it shows up as literal "[text](url)" text
    # on the page instead of a clickable link (same issue the home page
    # hit). Raw HTML <a> tags inside the list items render correctly.
    lines = ["# %s\n" % sidebar_domain["text"]]

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


def main():
    text = open(DOCS_TXT, encoding="utf-8").read()
    lines = text.split("\n")

    domains = []          # [{title, groups: [{title, posts: [{title, id}]}]}]
    cur_domain = cur_group = None
    ungrouped_posts = []  # posts directly under a domain, no L2 group

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
    print("domains=%d groups=%d posts=%d" % (
        len(domains), sum(len(d["groups"]) for d in domains), total_posts))

    os.makedirs(OUT_DOCS, exist_ok=True)
    sidebar = []
    missing_content = []

    for domain in domains:
        domain_slug = slugify_path(domain["title"])
        domain_dir = os.path.join(OUT_DOCS, domain_slug)
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
                link = "/%s/%s" % (domain_slug, post_slug)
                group_items.append({"text": post["title"], "link": link})

            if group["title"] is None:
                sidebar_domain["items"].extend(group_items)
            else:
                sidebar_domain["items"].append({
                    "text": group["title"], "collapsed": True, "items": group_items,
                })

        sidebar.append(sidebar_domain)
        write_domain_index(domain_dir, sidebar_domain)

    with open(os.path.join(os.path.dirname(OUT_DOCS) or ".", "sidebar.json"),
              "w", encoding="utf-8") as f:
        json.dump(sidebar, f, ensure_ascii=False, indent=2)

    print("missing content (%d):" % len(missing_content))
    for m in missing_content:
        print(" -", m)


if __name__ == "__main__":
    main()
