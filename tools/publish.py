#!/usr/bin/env python3
"""git commit + push using the GitHub settings from config.json.

Creates the git repository and the "origin" remote if they don't exist yet,
so a fresh copy of this folder only needs the repository URL filled in.
Login is left to git itself (Git Credential Manager opens a browser the
first time); no password or token is ever stored by this tool.
"""
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
        fail("git push failed - see the message above. (Is the repository URL "
             "right, and are you logged in to GitHub?)")
    print("Pushed to %s (%s)." % (url or "origin", branch))


if __name__ == "__main__":
    main()
