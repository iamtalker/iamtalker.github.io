#!/usr/bin/env python3
"""
Builds every book found in pages/github_io_books/*.txt into the shared
docs/ tree. Adding a new book means dropping a new DokuWiki-syntax file
into that folder - nothing else. No new script, no editing this file, no
registry to update by hand.

Each book file uses DokuWiki heading + page-include syntax:
  ====== domain ======      (a "chapter")
  ===== theme =====         (an optional grouping within a chapter)
  ==== post title ====      (an individual essay)
  {{page>NAMESPACE:id}}     (or bare page>NAMESPACE:id, brace-stripped is ok)

Unlike the original single-book version, a heading at ANY of these three
levels can itself be a "leaf" (an actual post) instead of a container, if
its own body - the lines directly under it, before any deeper heading -
already has a page> reference or real inline text. This is what lets a
loosely-structured document (headings with a bare reference straight
underneath, no wrapping theme/post levels; or a theme with hand-written
prose instead of an include) still work, not just the tidy 3-level shape
the first book (자유로의 초대) happens to use everywhere.

References aren't limited to wordblock: any DokuWiki namespace works
(bare id, :id, scrapbook:id, journal:2020-01:2020-01-01, etc. - colons
become path separators under pages/, same as DokuWiki itself), and an
optional #anchor pulls just that one heading's section out of the target
page instead of the whole thing (approximate match, like the id/anchor
handling in this user's other search tools - won't be byte-perfect for
every possible heading, but handles ordinary cases fine).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

PAGES_DIR = r"C:\MyData\DokuWikiStick\dokuwiki\data\pages"
BOOKS_SRC_DIR = os.path.join(PAGES_DIR, "github_io_books")
MEDIA_DIR = os.path.join(os.path.dirname(PAGES_DIR), "media")
OUT_DOCS = sys.argv[1] if len(sys.argv) > 1 else r"docs"
PANDOC = r"C:\Users\misti\AppData\Local\Pandoc\pandoc.exe"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(REPO_ROOT, "docs", "public")

HEADER_RE = re.compile(r"^(={2,6})(?!=)\s*(.+?)\s*\1(?!=)\s*$")
REF_RE = re.compile(r"page>([^&\n}]+)(&[^\n}]*)?")


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


def dokuwiki_anchor_slug(text):
    # approximates how DokuWiki turns a heading into a #section anchor -
    # not byte-perfect for every punctuation edge case, same caveat noted
    # for this tool's dokuAnchor() precedent.
    s = text.strip().lower()
    s = re.sub(r"[^\w\s\uac00-\ud7a3]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s


def parse_headers(lines):
    headers = []
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if m:
            headers.append((i, len(m.group(1)), m.group(2).strip()))
    return headers


def find_ref(body_lines):
    for line in body_lines:
        m = REF_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


def has_content(body_lines):
    return any(l.strip() for l in body_lines)


def resolve_ref_path(raw_ref):
    ref = raw_ref.strip()
    ref = ref.split("&", 1)[0]  # strip include-plugin flags (&noheader, &noindent, ...)
    anchor = None
    if "#" in ref:
        ref, anchor = ref.split("#", 1)
    ref = ref.lstrip(":")
    segments = [clean_id(s) for s in ref.split(":") if s.strip()]
    if not segments:
        return None, None
    path = os.path.join(PAGES_DIR, *segments) + ".txt"
    return path, anchor


def extract_anchor_section(raw_text, anchor):
    lines = raw_text.split("\n")
    headers = parse_headers(lines)
    target = dokuwiki_anchor_slug(anchor)
    for idx, (line_idx, count, title) in enumerate(headers):
        if dokuwiki_anchor_slug(title) == target or title.strip() == anchor.strip():
            end_line = len(lines)
            for j in range(idx + 1, len(headers)):
                if headers[j][1] >= count:
                    end_line = headers[j][0]
                    break
            return "\n".join(lines[line_idx:end_line])
    return None  # anchor not found - caller falls back to the whole page


INCLUDE_RE = re.compile(r"\{\{page>([^}]*)\}\}")


def renumber_headers(text, target_shallowest):
    # DokuWiki numbers a page's headers as if it always started at the
    # top of a document (its own top header is usually "======", however
    # deep it ends up embedded elsewhere via {{page>...}}). Once
    # transcluded under some other header, they need to be pushed deeper
    # to actually nest under it - DokuWiki's own include plugin does this
    # shift automatically; this reproduces it. Shifts every header in
    # `text` by the same delta so its shallowest (largest "=" count)
    # header becomes exactly `target_shallowest`, preserving the
    # relative depth of everything else in it. Returns the rewritten
    # text plus {line_index: new_count} for every header line touched,
    # so the caller can track the current header context line-by-line.
    lines = text.split("\n")
    headers = parse_headers(lines)
    if not headers:
        return text, {}
    # the SHALLOWEST header has the MOST "=" signs (DokuWiki's "======"
    # is its top level, "==" its deepest) - so the anchor for the shift
    # is the maximum count present, not the minimum.
    delta = target_shallowest - max(h[1] for h in headers)
    new_counts = {}
    for line_idx, count, htitle in headers:
        new_count = max(2, min(6, count + delta))
        new_counts[line_idx] = new_count
        if new_count != count:
            eq = "=" * new_count
            lines[line_idx] = "%s %s %s" % (eq, htitle, eq)
    return "\n".join(lines), new_counts


def expand_includes(raw_text, target_shallowest, seen):
    # {{page>...}} is a real DokuWiki transclusion - the referenced
    # page's own text belongs in place of the macro, renumbered (see
    # renumber_headers) to land one level under whatever header it was
    # found beneath, and resolved recursively (a hub page like this
    # book's "페미니즘 비판" domain is itself just a list of further
    # {{page>...}} references). `seen` (already-expanded file paths)
    # stops an include cycle from recursing forever.
    text, new_counts = renumber_headers(raw_text, target_shallowest)
    lines = text.split("\n")
    cur_ctx = target_shallowest
    out = []
    for i, line in enumerate(lines):
        if i in new_counts:
            cur_ctx = new_counts[i]
            out.append(line)
            continue
        m = INCLUDE_RE.fullmatch(line.strip())
        if not m:
            out.append(line)
            continue
        path, anchor = resolve_ref_path(m.group(1))
        if path is None or not os.path.exists(path) or path in seen:
            continue
        inner = open(path, encoding="utf-8").read()
        if anchor:
            section = extract_anchor_section(inner, anchor)
            if section is not None:
                inner = section
        out.append(expand_includes(inner, cur_ctx - 1, seen | {path}))
    return "\n".join(out)


def convert_dokuwiki(raw_text, title=None, ctx_count=6, seen=frozenset()):
    # ctx_count is the "=" count of the header (in the book file, or a
    # header this content was itself transcluded under) that this body
    # belongs to - its own headers get renumbered to sit one level under
    # it. Plain inline text (no ctx_count meaning, e.g. a book file's
    # hand-written paragraph) has no headers to renumber anyway.
    raw_text = expand_includes(raw_text, ctx_count - 1, seen)
    # pandoc's dokuwiki reader treats any {{...}} as a media/image
    # reference (core DokuWiki {{image.png}} syntax) - it doesn't know
    # about plugin macros like {{tag>...}}, so those turn into a broken
    # image link (e.g. ![](tag>foo)) that VitePress then tries to
    # resolve as a file import and fails the build. Strip any remaining
    # "{{word>...}}" plugin macro before conversion (page> includes are
    # already resolved above) - genuine image syntax is always
    # "{{namespace:file.ext}}" (colons, no ">"), so this can't eat real
    # images by mistake.
    raw_text = re.sub(r"\{\{\w+>[^}]*\}\}", "", raw_text)
    result = subprocess.run(
        [PANDOC, "-f", "dokuwiki", "-t", "gfm"],
        input=raw_text, capture_output=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError("pandoc failed: %s" % result.stderr)
    md = result.stdout
    # a leading heading is only stripped when it's a duplicate of the post
    # title already shown above the content (the usual case for this
    # user's wordblock articles, which are self-titled and included with
    # &noheader specifically to avoid this duplication - our pandoc-based
    # pipeline doesn't act on that flag, so it approximates it here). Old
    # freeform wiki hub pages often start with a real, DIFFERENT heading
    # (e.g. a page titled "여성혐오" whose own first header is "메갈의
    # 여성혐오") - stripping unconditionally silently deleted that heading.
    # The match is punctuation/whitespace-insensitive because the same
    # title is sometimes typed slightly differently between the outer
    # book file and the article's own header (a trailing period, spacing
    # around a dash, etc.) - see normalize_heading().
    m = re.match(r"^#+\s+(.+?)\s*\n+", md)
    if m and title and normalize_heading(m.group(1)) == normalize_heading(title):
        md = md[m.end():]
    localize_media(md)
    return md.strip()


# pandoc turns a bare DokuWiki media reference ({{namespace:file.ext}},
# no ">") into a root-relative markdown or raw-HTML image pointing at
# "/namespace/file.ext" - convenient, because that's exactly the URL a
# file placed under VitePress's docs/public/ would be served at. So
# there's nothing to rewrite, just a copy to make: find the real file
# under DokuWiki's own media/ tree (parallel to pages/) and place it at
# the matching path under public/.
IMAGE_SRC_RE = re.compile(r'!\[[^\]]*\]\((/[^)\s"]+)|<img\b[^>]*\bsrc="(/[^"]+)"')


def localize_media(md):
    for m in IMAGE_SRC_RE.finditer(md):
        rel = (m.group(1) or m.group(2)).lstrip("/")
        segments = rel.split("/")
        src = os.path.join(MEDIA_DIR, *segments)
        if not os.path.exists(src):
            continue  # broken reference - leave it, same tolerance as a missing page
        dest = os.path.join(PUBLIC_DIR, *segments)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)


def normalize_heading(s):
    s = s.strip().lower()
    return re.sub(r"[^\w가-힣]", "", s, flags=re.UNICODE)


MD_HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)


# characters markdown-it-anchor (VitePress's slugifier) treats as word
# separators - collapsed into a single "-" wherever one or more appear,
# confirmed against the real built HTML (this is why a DokuWiki header
# written with underscores, "귀납법적_착시로_...", or a colon, "번역:
# 여성혐오", lands as hyphens in the real id, not deleted or left as-is).
SLUG_SEPARATOR_RE = re.compile(
    r"[\s~`!@#$%^&*()\-_+=\[\]{}|\\;:\"'<>,.?/…]+"
)
# curly/smart quotes are dropped outright (no hyphen left behind) -
# confirmed against a real news-headline-style heading ("최고"...OECD)
# where the quote around "최고" vanishes but the "..." after it becomes
# a hyphen (handled by … above).
SLUG_DROP_RE = re.compile(r"[‘’“”]")


def vitepress_slug(text, seen):
    # approximates the id markdown-it-anchor (what VitePress's own
    # in-page outline links against) assigns a heading - not guaranteed
    # byte-perfect for every possible heading text (same caveat as this
    # tool's other approximate slug function, dokuwiki_anchor_slug), but
    # matches the ordinary cases seen in this corpus (verified against
    # every generated sidebar link's target actually existing in the
    # built HTML). Verify the same way if a new book's links don't jump
    # correctly.
    s = text.strip().lower()
    s = SLUG_DROP_RE.sub("", s)
    s = SLUG_SEPARATOR_RE.sub("-", s).strip("-")
    s = re.sub(r"-+", "-", s) or "section"
    if s[0].isdigit():
        # a bare-numeric-leading id isn't valid HTML4, so the slugifier
        # VitePress uses prefixes it with "_" (e.g. "2006-2011..." ->
        # "_2006-2011...") - confirmed against the actual built HTML.
        s = "_" + s
    # VitePress's real heading ids are Unicode NFD (decomposed Hangul
    # jamo, not the precomposed syllables our source text uses) - some
    # slugify step in its toolchain normalizes this way. Without this,
    # every Korean sidebar anchor link would silently fail to scroll to
    # its heading despite looking identical on screen. Confirmed against
    # the actual built HTML's id attributes.
    s = unicodedata.normalize("NFD", s)
    n = seen.get(s, 0)
    seen[s] = n + 1
    return s if n == 0 else "%s-%d" % (s, n)


def sidebar_leaf_entry(title, link, md):
    sub_items = build_heading_sidebar(md, link)
    if sub_items:
        return {"text": title, "link": link, "collapsed": True, "items": sub_items}
    return {"text": title, "link": link}


def build_heading_sidebar(md, base_link):
    # Mirrors the page's own in-page outline (VitePress's right-side "이
    # 글의 목차") as a left-sidebar tree of same-page anchor links, so a
    # domain's real internal structure (however deep - this is what
    # {{page>...}} pulls in, not something this book file's own headers
    # controlled) is visible without opening the page first.
    seen = {}
    items = []
    stack = [(1, items)]  # sentinel below h2, the shallowest heading level kept
    for m in MD_HEADING_RE.finditer(md):
        level = len(m.group(1))
        text = m.group(2).strip()
        slug = vitepress_slug(text, seen)
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        node = {"text": text, "link": "%s#%s" % (base_link, slug), "items": []}
        stack[-1][1].append(node)
        stack.append((level, node["items"]))
    def drop_empty(nodes):
        for n in nodes:
            if n["items"]:
                drop_empty(n["items"])
            else:
                del n["items"]
        return nodes
    return drop_empty(items)


def get_leaf_markdown(ref, inline_body, title, ctx_count):
    """Returns markdown text for a leaf post, or raises FileNotFoundError /
    RuntimeError with a message explaining why (caller reports it as
    missing content, keeps going). ctx_count is the "=" count of the
    header (in the book file) that defines this leaf - the referenced
    content's own headers get renumbered to sit one level under it."""
    if ref:
        path, anchor = resolve_ref_path(ref)
        if path is None or not os.path.exists(path):
            raise FileNotFoundError("no file for reference %r (looked for %s)" % (ref, path))
        raw = open(path, encoding="utf-8").read()
        if anchor:
            section = extract_anchor_section(raw, anchor)
            if section is not None:
                raw = section
        return convert_dokuwiki(raw, title=title, ctx_count=ctx_count, seen=frozenset({path}))
    else:
        return convert_dokuwiki("\n".join(inline_body), title=title)


def write_container_index(out_dir, title, items, prev_sibling, next_sibling, chapter_labels):
    # Plain markdown link syntax ([text](url)) doesn't get parsed inside
    # VitePress content here - it shows up as literal "[text](url)" text
    # on the page instead of a clickable link. Raw HTML <a> tags inside
    # the list items render correctly.
    lines = []
    frontmatter = {}
    prefix = "이전 장: " if chapter_labels else "이전: "
    next_prefix = "다음 장: " if chapter_labels else "다음: "
    if prev_sibling:
        frontmatter["prev"] = {"text": prefix + prev_sibling[0], "link": prev_sibling[1]}
    if next_sibling:
        frontmatter["next"] = {"text": next_prefix + next_sibling[0], "link": next_sibling[1]}
    lines.append("---")
    lines.append("giscus: false")  # a table of contents isn't a page to comment on
    for key in ("prev", "next"):
        if key in frontmatter:
            lines.append("%s:" % key)
            lines.append("  text: %s" % json.dumps(frontmatter[key]["text"], ensure_ascii=False))
            lines.append("  link: %s" % json.dumps(frontmatter[key]["link"], ensure_ascii=False))
    lines.append("---\n")
    lines.append("# %s\n" % title)

    def walk(nodes):
        for it in nodes:
            if "link" in it:
                lines.append('- <a href="%s">%s</a>' % (it["link"], it["text"]))
            else:
                lines.append("\n**%s**\n" % it["text"])
                walk(it["items"])

    walk(items)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def write_book_index(out_docs, book_slug, sidebar):
    # a leaf domain always has "link" (its one page), whether or not it
    # also carries "items" for its own internal heading sub-tree now -
    # only a true container domain (own folder, no single page) lacks it.
    lines = ['<li><a href="/%s/%s">%s</a></li>' % (book_slug, d["text"], d["text"])
             if "link" in d else
             '<li><a href="/%s/%s/">%s</a></li>' % (book_slug, d["text"], d["text"])
             for d in sidebar]
    home = """---
layout: home
hero:
  name: "%s"
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
""" % (book_slug, "\n".join(lines))

    book_dir = os.path.join(out_docs, book_slug)
    os.makedirs(book_dir, exist_ok=True)
    with open(os.path.join(book_dir, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(home)


def build_one_book(book_slug, docs_txt):
    lines = open(docs_txt, encoding="utf-8").read().split("\n")
    headers = parse_headers(lines)
    headers.append((len(lines), 999, None))  # sentinel, closes any open section

    # top-level (domain) headers: those not nested inside another header.
    # A header's span runs until the next header at count >= its own.
    top = []
    m = 0
    while m < len(headers) - 1:
        count = headers[m][1]
        end_idx = m + 1
        while headers[end_idx][1] < count:
            end_idx += 1
        top.append((m, end_idx))
        m = end_idx

    missing = []
    flat_posts = []  # [{file_path, title, link, chapter_title}] doc order, leaves only
    sidebar_items = []  # top-level sidebar entries for this book

    def domain_link_leaf(slug):
        return "/%s/%s" % (book_slug, slug)

    def domain_link_container(slug):
        return "/%s/%s/" % (book_slug, slug)

    # pass 1: figure out, for each domain, whether it's a leaf or a
    # container, and if a container, whether each of its groups is
    # itself a leaf or a container of posts. Written out immediately
    # (content doesn't depend on siblings), sidebar + flat_posts recorded
    # for the prev/next pass afterwards.
    domain_entries = []  # (title, slug, kind, extra) for the prev/next pass
    for di, (di_idx, di_end) in enumerate(top):
        d_line, d_count, d_title = headers[di_idx]
        d_slug = slugify_path(d_title)

        # children of this domain
        children = []
        k = di_idx + 1
        while k < di_end:
            c_count = headers[k][1]
            c_end = k + 1
            while headers[c_end][1] < c_count:
                c_end += 1
            children.append((k, c_end))
            k = c_end

        own_body_end = headers[children[0][0]][0] if children else headers[di_end][0]
        own_body = lines[d_line + 1: own_body_end]
        own_ref = find_ref(own_body)

        if not children and (own_ref or has_content(own_body)):
            # domain is itself a post
            file_path = os.path.join(OUT_DOCS, book_slug, d_slug + ".md")
            try:
                md = get_leaf_markdown(own_ref, own_body, d_title, d_count)
            except Exception as e:
                missing.append("%s: %s" % (d_title, e))
                continue
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("# %s\n\n%s\n" % (d_title, md))
            link = domain_link_leaf(d_slug)
            sidebar_items.append(sidebar_leaf_entry(d_title, link, md))
            flat_posts.append({"file_path": file_path, "title": d_title, "link": link, "chapter_title": d_title})
            domain_entries.append((d_title, "leaf", link))
            continue

        # domain is a container of groups
        domain_dir = os.path.join(OUT_DOCS, book_slug, d_slug)
        group_items = []
        for gi_idx, gi_end in children:
            g_line, g_count, g_title = headers[gi_idx]
            g_slug = slugify_path(g_title)

            grandchildren = []
            k2 = gi_idx + 1
            while k2 < gi_end:
                p_count = headers[k2][1]
                p_end = k2 + 1
                while headers[p_end][1] < p_count:
                    p_end += 1
                grandchildren.append((k2, p_end))
                k2 = p_end

            g_own_body_end = headers[grandchildren[0][0]][0] if grandchildren else headers[gi_end][0]
            g_own_body = lines[g_line + 1: g_own_body_end]
            g_own_ref = find_ref(g_own_body)

            if not grandchildren and (g_own_ref or has_content(g_own_body)):
                # this "theme" heading is itself a post, no posts under it
                file_path = os.path.join(domain_dir, g_slug + ".md")
                try:
                    md = get_leaf_markdown(g_own_ref, g_own_body, g_title, g_count)
                except Exception as e:
                    missing.append("%s / %s: %s" % (d_title, g_title, e))
                    continue
                os.makedirs(domain_dir, exist_ok=True)
                with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write("# %s\n\n%s\n" % (g_title, md))
                link = "/%s/%s/%s" % (book_slug, d_slug, g_slug)
                group_items.append(sidebar_leaf_entry(g_title, link, md))
                flat_posts.append({"file_path": file_path, "title": g_title, "link": link, "chapter_title": d_title})
                continue

            # ordinary group of posts
            post_items = []
            for pi_idx, pi_end in grandchildren:
                p_line, p_count, p_title = headers[pi_idx]
                p_slug = slugify_path(p_title)
                p_body = lines[p_line + 1: headers[pi_end][0]]
                p_ref = find_ref(p_body)
                if not p_ref and not has_content(p_body):
                    missing.append("%s / %s / %s: empty" % (d_title, g_title, p_title))
                    continue
                file_path = os.path.join(domain_dir, p_slug + ".md")
                try:
                    md = get_leaf_markdown(p_ref, p_body, p_title, p_count)
                except Exception as e:
                    missing.append("%s / %s / %s: %s" % (d_title, g_title, p_title, e))
                    continue
                os.makedirs(domain_dir, exist_ok=True)
                with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write("# %s\n\n%s\n" % (p_title, md))
                link = "/%s/%s/%s" % (book_slug, d_slug, p_slug)
                post_items.append(sidebar_leaf_entry(p_title, link, md))
                flat_posts.append({"file_path": file_path, "title": p_title, "link": link, "chapter_title": d_title})

            if post_items:
                group_items.append({"text": g_title, "collapsed": False, "items": post_items})

        sidebar_items.append({"text": d_title, "items": group_items})
        domain_entries.append((d_title, "container", domain_dir, group_items))

    # pass 2: chapter (top-level domain) prev/next, for both leaf domains
    # and container domains' own index.md
    for i, entry in enumerate(domain_entries):
        prev_e = domain_entries[i - 1] if i > 0 else None
        next_e = domain_entries[i + 1] if i < len(domain_entries) - 1 else None
        prev_sibling = (prev_e[0], prev_e[2] if prev_e[1] == "leaf" else domain_link_container(slugify_path(prev_e[0]))) if prev_e else None
        next_sibling = (next_e[0], next_e[2] if next_e[1] == "leaf" else domain_link_container(slugify_path(next_e[0]))) if next_e else None
        if entry[1] == "container":
            _, _, domain_dir, group_items = entry
            write_container_index(domain_dir, entry[0], group_items, prev_sibling, next_sibling, chapter_labels=True)

    # pass 3: prev/next footer links for every leaf post, chained across
    # the whole book in reading order - crossing from the last post of one
    # chapter straight into the first post of the next.
    for i, post in enumerate(flat_posts):
        frontmatter = {}
        if i > 0:
            prev = flat_posts[i - 1]
            label = prev["title"]
            if prev["chapter_title"] != post["chapter_title"]:
                label = "이전 장: %s" % prev["chapter_title"]
            frontmatter["prev"] = {"text": label, "link": prev["link"]}
        if i < len(flat_posts) - 1:
            nxt = flat_posts[i + 1]
            label = nxt["title"]
            if nxt["chapter_title"] != post["chapter_title"]:
                label = "다음 장: %s" % nxt["chapter_title"]
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

    write_book_index(OUT_DOCS, book_slug, sidebar_items)

    print("[%s] chapters=%d posts=%d" % (book_slug, len(top), len(flat_posts)))
    print("[%s] missing content (%d):" % (book_slug, len(missing)))
    for msg in missing:
        print(" -", msg)

    return sidebar_items


def main():
    os.makedirs(OUT_DOCS, exist_ok=True)
    book_files = sorted(glob.glob(os.path.join(BOOKS_SRC_DIR, "*.txt")))
    if not book_files:
        print("no books found in %s" % BOOKS_SRC_DIR)
        return

    # removing a book is the mirror of adding one: delete its .txt and
    # nothing else. Prune any docs/<slug> output left over from a book
    # file that's since been deleted, so it stops being served.
    current_slugs = {os.path.splitext(os.path.basename(p))[0].replace("_", " ") for p in book_files}
    for entry in os.listdir(OUT_DOCS):
        full = os.path.join(OUT_DOCS, entry)
        if os.path.isdir(full) and not entry.startswith(".") and entry != "public" and entry not in current_slugs:
            shutil.rmtree(full)
            print("removed stale book output: %s" % entry)

    all_sidebars = {}
    books = []
    for path in book_files:
        filename = os.path.splitext(os.path.basename(path))[0]
        book_slug = filename.replace("_", " ")
        sidebar = build_one_book(book_slug, path)
        all_sidebars[book_slug] = sidebar
        books.append({"slug": book_slug})

    with open(os.path.join(REPO_ROOT, "sidebar.json"), "w", encoding="utf-8") as f:
        json.dump(all_sidebars, f, ensure_ascii=False, indent=2)
    with open(os.path.join(REPO_ROOT, "books.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

    print("built %d book(s): %s" % (len(books), ", ".join(b["slug"] for b in books)))


if __name__ == "__main__":
    main()
