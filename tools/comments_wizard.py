#!/usr/bin/env python3
"""Comment (giscus) wizard: turns the comment box on or off, one step at a time.

Only touches the "giscus" part of site.json. Opened by the [댓글 설정] button.
"""
import os
import re
import sys
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from ui import Pager, entry_row, open_btn, text  # noqa: E402


def clean_repo(s):
    """'owner/name' from a pasted repo, clone URL or browser URL."""
    return re.sub(r"(^https?://github\.com/|\.git$|/$)", "", s.strip())


def parse_giscus(code):
    """The data-* values from a pasted giscus <script> tag."""
    found = {}
    for attr in ("repo", "repo-id", "category", "category-id"):
        m = re.search(r'data-%s\s*=\s*"([^"]*)"' % attr, code)
        if m:
            found[attr] = m.group(1).strip()
    return found


def run():
    """Show the wizard. Returns True if site.json was saved."""
    local, site = config.load_local(), config.load_site()
    g = site.get("giscus") or {}
    saved = {"ok": False}

    root = tk.Tk()
    root.title("댓글 설정")
    root.geometry("640x560")
    root.minsize(600, 500)

    m = re.match(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", local["git_remote"].strip())
    v = {
        "use": tk.StringVar(value="on"),
        "repo": tk.StringVar(value=g.get("repo") or (m.group(1) if m else "")),
        "repoId": tk.StringVar(value=g.get("repoId", "")),
        "category": tk.StringVar(value=g.get("category") or "Announcements"),
        "categoryId": tk.StringVar(value=g.get("categoryId", "")),
    }
    pasted = {"text": ""}

    def repo():
        return clean_repo(v["repo"].get())

    def page_use():
        text(body(), "사이트 글 아래에 댓글창을 둘까요?", strong=True)
        ttk.Radiobutton(body(), text="댓글창 사용 (방문자가 GitHub 계정으로 로그인해서 댓글을 씁니다)",
                        value="on", variable=v["use"]).pack(anchor="w", pady=2)
        ttk.Radiobutton(body(), text="댓글창 사용 안 함", value="off",
                        variable=v["use"]).pack(anchor="w", pady=2)
        text(body(), "댓글은 GitHub의 'Discussions'에 저장되고 giscus 라는 무료 서비스가 화면에 보여 줍니다.\n"
                     "아래 단계에서 GitHub 쪽 준비(앱 설치, Discussions 켜기)를 안내합니다.", pady=(14, 0))
        if g.get("repo") and g.get("repoId"):
            text(body(), "지금 설정: %s 에서 켜져 있습니다." % g["repo"], pady=(8, 0))
        return lambda: True

    def page_github():
        text(body(), "GitHub에서 두 가지를 한 번만 해 두세요.", strong=True)
        text(body(), "댓글이 저장될 저장소를 '아이디/저장소이름' 형태로 쓰세요. (보통 내 사이트 저장소)\n"
                     "https://github.com/ 나 .git 은 붙이지 않습니다.", pady=(0, 2))
        entry_row(body(), "댓글 저장소", v["repo"], width=34)

        def need_repo():
            if not re.match(r"^[^/\s]+/[^/\s]+$", repo()):
                messagebox.showerror("댓글 저장소", "'아이디/저장소이름' 형태로 먼저 적어 주세요.\n예: honggildong/honggildong.github.io")
                return False
            return True

        text(body(), "① giscus 앱 설치 — 열리는 화면에서 'Only select repositories'를 고르고\n"
                     "   위 저장소를 선택한 뒤 Install.", pady=(10, 2))
        open_btn(body(), "giscus 앱 설치 페이지 열기", lambda: "https://github.com/apps/giscus")
        text(body(), "② Discussions 켜기 — 열리는 화면의 Features 항목에서 Discussions 에 체크.\n"
                     "   (저장소는 Public 이어야 합니다.)", pady=(8, 2))
        open_btn(body(), "Discussions 켜는 페이지 열기",
                 lambda: "https://github.com/%s/settings#features" % repo() if need_repo() else None)
        return need_repo

    def page_make():
        text(body(), "giscus.app 에서 설정 코드를 만듭니다.", strong=True)
        text(body(), "아래 버튼으로 giscus.app 을 열고 차례대로 하세요.\n\n"
                     "1. '저장소' 칸에 앞 단계에서 적은 내 저장소를 입력:  %s\n"
                     "   (형태 예: honggildong/honggildong.github.io)\n"
                     "   성공 문구가 나오면 앱 설치와 Discussions 가 제대로 된 것입니다.\n"
                     "2. '페이지 ↔ Discussion 연결 방식'은 그대로 둡니다 (pathname).\n"
                     "3. 'Discussion 카테고리'에서 Announcements 를 고릅니다.\n"
                     "4. 페이지를 맨 아래로 내리면 '<script src=\"https://giscus.app/client.js\" …>'\n"
                     "   코드가 나옵니다. 그 코드를 통째로 복사하세요." % (repo() or "아이디/저장소이름"),
             pady=(0, 8))
        open_btn(body(), "giscus.app 열기", lambda: "https://giscus.app/ko")
        return lambda: True

    def page_paste():
        text(body(), "복사한 코드를 붙여넣으세요.", strong=True)
        box = tk.Text(body(), height=7, width=60)
        box.pack(fill="x", pady=(0, 6))
        box.insert("1.0", pasted["text"])
        result = text(body(), "", pady=(0, 0))

        def read(*_):
            pasted["text"] = box.get("1.0", "end")
            f = parse_giscus(pasted["text"])
            if "repo" in f:
                v["repo"].set(clean_repo(f["repo"]))
            if "repo-id" in f:
                v["repoId"].set(f["repo-id"])
            if "category" in f:
                v["category"].set(f["category"])
            if "category-id" in f:
                v["categoryId"].set(f["category-id"])
            return f

        def fill():
            f = read()
            if "repo-id" in f and "category-id" in f:
                result.set_text("✔ 값을 읽었습니다.\n저장소: %s\n카테고리: %s\nrepo ID: %s\n카테고리 ID: %s"
                                % (v["repo"].get(), v["category"].get(), v["repoId"].get(), v["categoryId"].get()))
            else:
                result.set_text("✘ data-repo-id / data-category-id 를 찾지 못했습니다.\n"
                                "giscus.app 맨 아래의 <script …> 코드 전체를 복사해 붙여넣으세요.")
        ttk.Button(body(), text="값 읽기", command=fill).pack(anchor="w", pady=(0, 6))
        if v["repoId"].get() and v["categoryId"].get():
            result.set_text("지금 저장된 값:\n저장소: %s\n카테고리: %s\nrepo ID: %s\n카테고리 ID: %s\n"
                            "(그대로 쓰려면 [다음])" % (v["repo"].get(), v["category"].get(),
                                                      v["repoId"].get(), v["categoryId"].get()))

        def validate():
            read()
            if not (v["repoId"].get().strip() and v["categoryId"].get().strip()):
                messagebox.showerror("코드", "코드를 붙여넣고 [값 읽기]로 repo ID 와 카테고리 ID 를 채워 주세요.")
                return False
            return True
        return validate

    def page_done():
        if v["use"].get() == "off":
            text(body(), "댓글창을 끕니다.", strong=True)
            text(body(), "[마침]을 누르면 저장됩니다. 사이트 글 아래에 댓글창이 나오지 않게 됩니다.\n"
                         "(이미 달린 댓글은 GitHub Discussions 에 그대로 남아 있습니다.)")
        else:
            text(body(), "댓글 설정이 끝났습니다.", strong=True)
            text(body(), "저장소: %s\n카테고리: %s" % (repo(), v["category"].get()))
            text(body(), "[마침]을 누르면 저장됩니다. 그다음 메인 창에서 [사이트에 올리기]를 하면\n"
                         "1~2분 뒤 글 아래에 댓글창이 나타납니다.")
        return lambda: True

    # the body frame is rebuilt for every page, so builders look it up when called
    def body():
        return pager.body

    pages = [("댓글 1 / 5  사용 여부", page_use), ("댓글 2 / 5  GitHub 준비", page_github),
             ("댓글 3 / 5  코드 만들기", page_make), ("댓글 4 / 5  코드 붙여넣기", page_paste),
             ("댓글 5 / 5  끝", page_done)]
    DONE = len(pages) - 1

    def route(i):
        if i == 0 and v["use"].get() == "off":
            return DONE           # nothing to set up
        return i + 1 if i < DONE else None

    def save():
        s = config.load_site()
        if v["use"].get() == "off":
            s["giscus"] = {"repo": "", "repoId": "", "category": v["category"].get() or "Announcements",
                           "categoryId": ""}
        else:
            s["giscus"] = {"repo": repo(), "repoId": v["repoId"].get().strip(),
                           "category": v["category"].get().strip() or "Announcements",
                           "categoryId": v["categoryId"].get().strip()}
        config.save_site(s)
        saved["ok"] = True
        root.destroy()

    pager = Pager(root, pages, save, route=route)
    pager.show(0)
    root.mainloop()
    return saved["ok"]


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
