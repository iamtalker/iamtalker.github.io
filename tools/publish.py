#!/usr/bin/env python3
"""git commit + push using the GitHub settings from config.json.

Creates the git repository and the "origin" remote if they don't exist yet,
so a fresh copy of this folder only needs the repository URL filled in.
Login is left to git itself (Git Credential Manager opens a browser the
first time); no password or token is ever stored by this tool.
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

ROOT = config.REPO_ROOT


def git(*args, capture=True):
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace",
        capture_output=capture,
    )


def fail(msg):
    print(msg)
    sys.exit(1)


def main():
    local = config.load_local()
    url = local["git_remote"].strip()
    branch = local["git_branch"].strip() or "main"
    message = local["commit_message"].strip() or "content update"

    if not shutil.which("git"):
        fail("git is not installed (https://git-scm.com/download/win).")

    if not os.path.isdir(os.path.join(ROOT, ".git")):
        r = git("init", "-b", branch)
        if r.returncode != 0:
            fail("git init failed:\n" + r.stderr)
        print("Initialized a new git repository.")

    current = git("remote", "get-url", "origin")
    if url:
        if current.returncode != 0:
            git("remote", "add", "origin", url)
        elif current.stdout.strip() != url:
            git("remote", "set-url", "origin", url)
    elif current.returncode != 0:
        fail("GitHub repository URL is not set - fill it in with settings.bat.")

    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("No changes to commit.")
        # still push: an earlier commit may not have reached GitHub yet
    else:
        r = git("commit", "-m", message)
        if r.returncode != 0:
            fail("git commit failed:\n" + r.stdout + r.stderr +
                 "\nIf git asks who you are, run:\n"
                 '  git config --global user.name "Your Name"\n'
                 '  git config --global user.email "you@example.com"')

    r = git("push", "-u", "origin", "HEAD:%s" % branch, capture=False)
    if r.returncode != 0:
        if remote_has_other_content(branch):
            merge_existing_remote(branch)
        fail("git push failed - see the message above. (Is the repository URL "
             "right, and are you logged in to GitHub?)")
    print("Pushed to %s (%s)." % (url or "origin", branch))


def book_slugs(text):
    try:
        return [b["slug"] for b in json.loads(text)]
    except (ValueError, KeyError, TypeError):
        return []


def remote_has_other_content(branch):
    """True when GitHub already holds commits we don't have (e.g. books
    published earlier from another folder), which is why the push bounced."""
    if git("fetch", "origin", branch).returncode != 0:
        return False
    ref = "origin/%s" % branch
    return git("merge-base", "--is-ancestor", ref, "HEAD").returncode != 0


def merge_existing_remote(branch):
    ref = "origin/%s" % branch
    remote_books = book_slugs(git("show", "%s:books.json" % ref).stdout)
    try:
        with open(os.path.join(ROOT, "books.json"), encoding="utf-8") as f:
            local_books = book_slugs(f.read())
    except OSError:
        local_books = []
    only_remote = [b for b in remote_books if b not in local_books]

    print()
    print("GitHub에는 이미 있지만 이 폴더에는 없는 내용이 있습니다:")
    for b in only_remote or ["(추가된 책은 없고 다른 파일만 있음)"]:
        print("  -", b)
    print("그 내용을 합쳐서 보존할까요? (겹치는 파일은 이 폴더 것이 우선)")
    if input("[y/N] ").strip().lower() != "y":
        fail("합치지 않았습니다. 아무것도 올리지 않았습니다.")

    r = git("merge", ref, "--allow-unrelated-histories", "-X", "ours",
            "-m", "Merge existing GitHub content")
    if r.returncode != 0:
        git("merge", "--abort")
        fail("합치기에 실패했습니다. 아무것도 바뀌지 않았습니다:\n" + r.stdout + r.stderr)

    print("합쳤습니다. 다음 빌드에서는 설정에 소스가 등록된 책만 남습니다.")
    if only_remote:
        print("settings.bat에서 아래 책들의 소스를 추가한 뒤 update.bat을 "
              "다시 실행하면 전부 빌드해서 올립니다:")
        for b in only_remote:
            print("  -", b)
    else:
        print("update.bat을 다시 실행하면 올라갑니다.")
    sys.exit(1)


if __name__ == "__main__":
    main()
