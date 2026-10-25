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


def ask(question):
    """y/n question. Under the app window (BOOK_GUI=1) the window shows the
    dialog: we print a marker line with the question and read its answer."""
    if os.environ.get("BOOK_GUI"):
        print("@@ASK@@" + json.dumps(question, ensure_ascii=False), flush=True)
        return sys.stdin.readline()
    return input(question + " [y/N] ")


def fail(msg):
    print(msg)
    sys.exit(1)


def main():
    local = config.load_local()
    url = local["git_remote"].strip()
    branch = local["git_branch"].strip() or "main"
    message = local["commit_message"].strip() or "content update"

    if not shutil.which("git"):
        fail("git 이 설치되어 있지 않습니다. https://git-scm.com/download/win 에서 설치하세요.")

    if not os.path.isdir(os.path.join(ROOT, ".git")):
        r = git("init", "-b", branch)
        if r.returncode != 0:
            fail("git 저장소를 만들지 못했습니다:\n" + r.stderr)
        print("새 git 저장소를 만들었습니다.")

    current = git("remote", "get-url", "origin")
    if url:
        if current.returncode != 0:
            git("remote", "add", "origin", url)
        elif current.stdout.strip() != url:
            git("remote", "set-url", "origin", url)
    elif current.returncode != 0:
        fail("GitHub 저장소 주소가 비어 있습니다. [설정]에서 입력하세요.")

    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("새로 바뀐 내용이 없습니다.")
        # still push: an earlier commit may not have reached GitHub yet
    else:
        r = git("commit", "-m", message)
        if r.returncode != 0:
            fail("git 커밋에 실패했습니다:\n" + r.stdout + r.stderr +
                 "\n'누구인지 모르겠다'는 메시지라면 아래를 한 번 실행하세요:\n"
                 '  git config --global user.name "Your Name"\n'
                 '  git config --global user.email "you@example.com"')

    r = git("push", "-u", "origin", "HEAD:%s" % branch, capture=False)
    if r.returncode != 0:
        if remote_has_other_content(branch):
            r = overwrite_remote(branch)
        if r.returncode != 0:
            fail("GitHub에 올리지 못했습니다. 위 메시지를 확인하세요.\n"
                 "(저장소 주소가 맞는지, GitHub에 로그인했는지 확인해 보세요.)")
    print("GitHub에 올렸습니다: %s (%s)" % (url or "origin", branch))


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


def overwrite_remote(branch):
    """Replace what GitHub holds with this folder, after one confirmation."""
    ref = "origin/%s" % branch
    remote_books = book_slugs(git("show", "%s:books.json" % ref).stdout)
    try:
        with open(os.path.join(ROOT, "books.json"), encoding="utf-8") as f:
            local_books = book_slugs(f.read())
    except OSError:
        local_books = []
    only_remote = [b for b in remote_books if b not in local_books]

    print()
    print("GitHub에는 이 폴더에 없는 내용이 이미 올라가 있습니다.")
    print("계속하면 GitHub의 기존 내용이 지워지고 이 폴더 내용으로 바뀝니다.")
    if only_remote:
        print("사라지는 책:")
        for b in only_remote:
            print("  -", b)
    question = "GitHub의 기존 내용을 지우고 이 폴더 내용으로 덮어쓸까요?"
    if only_remote:
        question += "\n\n사라지는 책:\n" + "\n".join("  - " + b for b in only_remote)
    if ask(question).strip().lower() != "y":
        fail("덮어쓰지 않았습니다. 아무것도 올리지 않았습니다.")

    # lease: refuse if someone pushed again after the fetch above
    return git("push", "-u", "--force-with-lease=%s:%s" % (branch, ref),
               "origin", "HEAD:%s" % branch, capture=False)


if __name__ == "__main__":
    main()
