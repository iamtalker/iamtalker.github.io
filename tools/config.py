"""Shared settings loader for the build scripts and the settings window.

Two files, both at the repo root:
  config.json - this machine's local settings (DokuWiki folder, pandoc path).
                Git-ignored: it is different on every computer.
  site.json   - what the published site looks like (title, tagline, language).
                Committed: the GitHub Actions build reads it, too.

Both are written by tools/settings_gui.py; nobody has to edit them by hand.
"""
import json
import os
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.json")
SITE_PATH = os.path.join(REPO_ROOT, "site.json")

DEFAULT_LOCAL = {
    "use_dokuwiki": True,     # source 1: DokuWiki book files -> markdown
    "use_markdown": False,    # source 2: markdown folders -> markdown
    "markdown_dir": "",       # folder whose sub-folders are books (see markdown_source.py)
    "books_dir": "",          # folder holding one .txt per book, inside .../dokuwiki/data/pages
    "media_dir": "",          # blank = sibling "media" folder next to the "pages" folder
    "pandoc": "",             # blank = look for "pandoc" on PATH
    "auto_push": True,        # [사이트에 올리기]: git commit + push after building
    "git_remote": "",         # e.g. https://github.com/<id>/<id>.github.io.git
    "git_branch": "main",     # branch GitHub Pages deploys from
    "commit_message": "content update",
}

DEFAULT_SITE = {
    "title": "",
    "tagline": "",
    "description": "",
    "lang": "ko-KR",
    # giscus comments (https://giscus.app); blank repo = no comment box
    "giscus": {"repo": "", "repoId": "", "category": "Announcements", "categoryId": ""},
}


def _load(path, defaults):
    data = dict(defaults)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data.update(json.load(f))
    return data


def _save(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_local():
    data = _load(CONFIG_PATH, DEFAULT_LOCAL)
    # older config.json kept the pages folder and the book sub-folder apart
    old_pages = data.pop("pages_dir", "")
    old_sub = data.pop("books_subdir", "")
    if not data["books_dir"] and old_pages:
        data["books_dir"] = os.path.normpath(os.path.join(old_pages, old_sub))
    return data


def load_site():
    return _load(SITE_PATH, DEFAULT_SITE)


def save_local(data):
    _save(CONFIG_PATH, data)


def save_site(data):
    _save(SITE_PATH, data)


def find_pandoc(configured=""):
    if configured and os.path.exists(configured):
        return configured
    return shutil.which("pandoc") or ""


def find_pages_root(books_dir):
    """The DokuWiki "pages" folder that contains books_dir: the nearest
    ancestor called "pages", else the parent of books_dir."""
    cur = os.path.normpath(books_dir)
    while True:
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.dirname(os.path.normpath(books_dir))
        if os.path.basename(cur).lower() == "pages":
            return cur
        cur = parent


def resolved_paths(local=None):
    """Absolute paths the build uses, derived from config.json."""
    local = local or load_local()
    books = local["books_dir"]
    pages = find_pages_root(books) if books else ""
    return {
        "pages_dir": pages,
        "books_src_dir": books,
        "media_dir": local["media_dir"] or os.path.join(os.path.dirname(pages), "media"),
        "pandoc": find_pandoc(local["pandoc"]),
    }


def require_ready():
    """Return resolved paths, or exit with a pointer to the settings window."""
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit("config.json not found - open the app (update.bat) and use [설정].")
    local = load_local()
    paths = resolved_paths(local)
    problems = []
    if not (local["use_dokuwiki"] or local["use_markdown"]):
        problems.append("No source is enabled.")
    if local["use_dokuwiki"]:
        if not os.path.isdir(paths["books_src_dir"]):
            problems.append("Books folder not found: %r" % paths["books_src_dir"])
        if not paths["pandoc"]:
            problems.append("pandoc not found (install it, or set its path in [설정])")
    if local["use_markdown"] and not os.path.isdir(local["markdown_dir"]):
        problems.append("Markdown folder not found: %r" % local["markdown_dir"])
    if problems:
        raise SystemExit("\n".join(problems + ["", "Fix these in [설정]."]))
    return paths
