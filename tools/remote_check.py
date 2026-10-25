"""Check a GitHub repository URL the way the settings window and the wizard need.

check() never raises: it returns (kind, message) where kind is one of
"ok", "warn", "error" so the caller only has to pick the dialog icon.
"""
import os
import re
import shutil
import subprocess

URL_RE = re.compile(r"https?://github\.com/[^/\s]+/[^/\s]+$")


def make_url(user, repo_name):
    return "https://github.com/%s/%s.git" % (user.strip(), repo_name.strip())


def check(url, branch="main"):
    url = url.strip()
    if not url:
        return "error", "저장소 주소를 입력하세요."
    if not URL_RE.match(url):
        hint = ""
        if re.match(r"^[^/\s:]+/[^/\s:]+$", url):
            hint = ("\n'아이디/저장소이름'만 쓰셨네요. 앞에 https://github.com/ 를 붙여\n"
                    "https://github.com/%s.git 형태로 쓰세요." % re.sub(r"\.git$", "", url))
        return "error", "주소 형태가 올바르지 않습니다.\n정확한 형태: https://github.com/아이디/저장소이름.git" + hint
    if not shutil.which("git"):
        return "error", "git이 설치되어 있지 않습니다. https://git-scm.com 에서 설치하세요."

    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        r = subprocess.run(
            ["git", "ls-remote", "--heads", url], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30, env=env)
    except subprocess.TimeoutExpired:
        return "error", "30초 안에 응답이 없습니다. 인터넷 연결을 확인하세요."

    if r.returncode != 0:
        err = r.stderr.strip()
        low = err.lower()
        if "could not resolve host" in low:
            why = "인터넷에 연결되어 있지 않거나 주소의 도메인이 틀렸습니다."
        elif "not found" in low or ("repository" in low and "exist" in low):
            why = ("GitHub에 이 저장소가 없습니다. 아이디나 저장소 이름의 철자를 확인하거나,\n"
                   "저장소를 아직 만들지 않았다면 먼저 만드세요. 비공개 저장소라면 아직 로그인 전일 수도 있습니다.")
        elif "authentication" in low or "terminal prompts disabled" in low or "403" in low:
            why = ("로그인이 필요한 저장소입니다. 첫 업로드 때 git이 브라우저로 로그인을 물어보니\n"
                   "그때 로그인하면 됩니다. (주소는 맞을 가능성이 높습니다.)")
        else:
            why = "주소가 틀렸거나 로그인이 필요할 수 있습니다."
        return "warn", "접근하지 못했습니다.\n\n" + why + "\n\n(git 메시지)\n" + err

    heads = [ln.split("refs/heads/")[-1] for ln in r.stdout.splitlines() if "refs/heads/" in ln]
    branch = branch.strip() or "main"
    if not heads:
        return "ok", "저장소에 접근할 수 있습니다.\n비어 있는 저장소라 바로 업로드할 수 있습니다."
    if branch not in heads:
        return "warn", ("저장소에 접근할 수 있습니다.\n하지만 '%s' 브랜치가 없고 '%s' 브랜치가 있습니다.\n"
                        "'브랜치' 칸을 '%s'로 바꾸거나, GitHub Pages가 쓰는 브랜치를 확인하세요."
                        % (branch, ", ".join(heads), heads[0]))
    return "ok", ("저장소에 접근할 수 있습니다.\n이미 올라간 내용이 있습니다. 처음 업로드할 때 거절되면\n"
                  "[사이트에 올리기]가 기존 내용을 지우고 덮어쓸지 물어봅니다.")
