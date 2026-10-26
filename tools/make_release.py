#!/usr/bin/env python3
"""Publish the tool itself (without anyone's books or settings) to its own repository.

  py tools/make_release.py              build the clean copy and show what would change
  py tools/make_release.py --push       also commit + push it to the release repository
  py tools/make_release.py --push --tag v0.2.0   ... and create a GitHub release

The clean copy is `git archive HEAD` of this folder, minus the books
(docs/<book>/, docs/public, books.json, sidebar.json, docs/index.md) and with
site.json back at its defaults. Nothing is read from the working tree, so
uncommitted edits and config.json can never leak into it: commit first.

The release repository defaults to <owner>/githubio_book, where <owner> comes
from this folder's own `origin` URL. Needs git, and the gh CLI for --tag.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

ROOT = config.REPO_ROOT


def run(args, cwd=ROOT, check=True, **kw):
    r = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                       capture_output=True, **kw)
    if check and r.returncode != 0:
        sys.exit("%s failed:\n%s%s" % (" ".join(args[:2]), r.stdout, r.stderr))
    return r


def owner_from_origin():
    url = run(["git", "remote", "get-url", "origin"]).stdout.strip()
    m = re.match(r"https?://github\.com/([^/]+)/", url)
    if not m:
        sys.exit("origin URL is not a GitHub address: %r (pass --repo)" % url)
    return m.group(1)


def export_clean(dest):
    """git archive HEAD -> dest, then strip books and personal settings."""
    os.makedirs(dest)
    arch = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True)
    if arch.returncode != 0:
        sys.exit("git archive failed: " + arch.stderr.decode("utf-8", "replace"))
    tar = os.path.join(dest, "_a.tar")
    with open(tar, "wb") as f:
        f.write(arch.stdout)
    run(["tar", "-xf", "_a.tar"], cwd=dest)
    os.remove(tar)

    docs = os.path.join(dest, "docs")
    for entry in os.listdir(docs):
        if entry != ".vitepress":      # book folders, public/, index.md: all regenerated or dropped
            p = os.path.join(docs, entry)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for name, text in (("books.json", "[]\n"), ("sidebar.json", "{}\n")):
        with open(os.path.join(dest, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    # site.json at defaults, then an empty library page built by the tool itself
    with open(os.path.join(dest, "site.json"), "w", encoding="utf-8", newline="\n") as f:
        import json
        json.dump(config.DEFAULT_SITE, f, ensure_ascii=False, indent=2)
        f.write("\n")
    run([sys.executable, os.path.join("tools", "build_library.py")], cwd=dest)
    shutil.rmtree(os.path.join(dest, "tools", "__pycache__"), ignore_errors=True)


def leak_check(dest, owner):
    """Refuse to publish if anything that looks personal slipped through."""
    needles = [owner, "MyData", "DokuWikiStick"]
    try:
        with open(os.path.join(ROOT, "books.json"), encoding="utf-8") as f:
            import json
            needles += [b["slug"] for b in json.load(f)]
    except (OSError, ValueError, KeyError):
        pass
    hits = []
    for dp, _dn, files in os.walk(dest):
        if os.sep + ".git" in dp or "package-lock" in dp:
            continue
        for fn in files:
            if fn == "package-lock.json":
                continue
            p = os.path.join(dp, fn)
            try:
                text = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for n in needles:
                if n and n in text:
                    hits.append("%s  contains %r" % (os.path.relpath(p, dest), n))
    if hits:
        sys.exit("Personal content would be published - fix the source first:\n  " + "\n  ".join(hits))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="release repository, owner/name (default: <owner>/githubio_book)")
    ap.add_argument("--push", action="store_true", help="commit and push (default: only show the diff)")
    ap.add_argument("--tag", help="also create a GitHub release with this tag (needs --push and gh)")
    ap.add_argument("-m", "--message", default="Sync from the working copy")
    a = ap.parse_args()

    if run(["git", "status", "--porcelain"]).stdout.strip():
        sys.exit("Uncommitted changes here - commit first (the release is built from HEAD).")
    owner = owner_from_origin()
    repo = a.repo or "%s/githubio_book" % owner
    url = "https://github.com/%s.git" % repo

    work = tempfile.mkdtemp(prefix="githubio_release_")
    try:
        export = os.path.join(work, "export")
        export_clean(export)
        leak_check(export, owner)

        clone = os.path.join(work, "repo")
        run(["git", "clone", "-q", url, clone])
        for entry in os.listdir(clone):                 # replace everything but .git
            if entry != ".git":
                p = os.path.join(clone, entry)
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        for entry in os.listdir(export):
            src, dst = os.path.join(export, entry), os.path.join(clone, entry)
            shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy2(src, dst)

        run(["git", "add", "-A"], cwd=clone)
        changes = run(["git", "status", "--short"], cwd=clone).stdout.strip()
        if not changes:
            print("No changes: %s is already up to date." % repo)
            return
        print("Changes for %s:\n%s" % (repo, changes))
        if not a.push:
            print("\n(dry run - add --push to publish)")
            return
        run(["git", "commit", "-q", "-m", a.message], cwd=clone)
        run(["git", "push", "-q", "origin", "HEAD"], cwd=clone)
        print("Pushed to %s." % url)
        if a.tag:
            r = run(["gh", "release", "create", a.tag, "--repo", repo, "--title", a.tag,
                     "--generate-notes"], check=False)
            print(r.stdout.strip() or r.stderr.strip())
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
