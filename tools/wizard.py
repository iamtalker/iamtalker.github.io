#!/usr/bin/env python3
"""First-run wizard: one question per screen, buttons that open the right
GitHub pages, and nothing to type that the program can work out itself.

Writes the same config.json / site.json the full settings window does
(settings_gui.py), so either one can be used afterwards.
"""
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import remote_check  # noqa: E402

WRAP = 540


def git_config_get(key):
    if not shutil.which("git"):
        return ""
    r = subprocess.run(["git", "config", "--global", key], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def run():
    """Show the wizard. Returns True if the settings were saved."""
    local = config.load_local()
    site = config.load_site()
    saved = {"ok": False}

    root = tk.Tk()
    root.title("처음 설정")
    root.geometry("640x560")
    root.minsize(600, 520)

    bg = ttk.Style().lookup("TFrame", "background") or root.cget("bg")
    note_font = tkfont.nametofont("TkDefaultFont")

    v = {
        "source": tk.StringVar(value="markdown" if local["use_markdown"] and not local["use_dokuwiki"]
                               else "dokuwiki"),
        "folder": tk.StringVar(value=local["books_dir"] if local["use_dokuwiki"] or not local["use_markdown"]
                               else local["markdown_dir"]),
        "git_name": tk.StringVar(value=git_config_get("user.name")),
        "git_email": tk.StringVar(value=git_config_get("user.email")),
        "user": tk.StringVar(),
        "repo": tk.StringVar(),
        "title": tk.StringVar(value=site["title"]),
        "tagline": tk.StringVar(value=site["tagline"]),
    }
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", local["git_remote"].strip())
    if m:
        v["user"].set(m.group(1))
        v["repo"].set(m.group(2))
    repo_touched = {"v": bool(m) and m.group(2) != m.group(1) + ".github.io"}

    def on_user(*_):
        if not repo_touched["v"]:
            u = v["user"].get().strip()
            repo_touched["auto"] = True
            v["repo"].set(u + ".github.io" if u else "")
            repo_touched["auto"] = False
    v["user"].trace_add("write", on_user)

    # ---- frame: header / page / buttons -----------------------------------
    head = ttk.Label(root, font=("", 11, "bold"), padding=(20, 16, 20, 4))
    head.pack(fill="x")
    body = ttk.Frame(root, padding=(20, 4, 20, 8))
    body.pack(fill="both", expand=True)
    bar = ttk.Frame(root, padding=(20, 8))
    bar.pack(fill="x")
    back_btn = ttk.Button(bar, text="← 이전")
    next_btn = ttk.Button(bar, text="다음 →")
    next_btn.pack(side="right")
    back_btn.pack(side="right", padx=6)

    # ---- small widgets ----------------------------------------------------
    def text(parent, s, strong=False, pady=(0, 6)):
        """Selectable (copyable) paragraph."""
        t = tk.Text(parent, height=1, width=60, wrap="word", relief="flat", borderwidth=0,
                    highlightthickness=0, background=bg, font=note_font if not strong else ("", 10, "bold"),
                    foreground="#222" if strong else "#444", cursor="xterm")
        t.insert("1.0", s)

        def fit(_e=None):
            n = t.count("1.0", "end-1c", "displaylines")
            # count() returns the display-line BREAKS between the two indexes: lines = breaks + 1
            t.configure(height=(n[0] if n else 0) + 1)

        def block(e):
            if (e.state & 0x4) and e.keysym.lower() in ("c", "a"):
                return None
            if e.keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
                return None
            return "break"
        def set_text(s):
            # replace the text AND re-fit the height, or a longer text gets cut off
            t.delete("1.0", "end")
            t.insert("1.0", s)
            t.update_idletasks()
            fit()
        t.set_text = set_text
        t.bind("<Key>", block)
        t.bind("<Configure>", fit)
        t.bind("<Button-1>", lambda e: t.focus_set())
        t.pack(fill="x", pady=pady)
        return t

    def open_btn(parent, label, url_fn):
        def go():
            url = url_fn()
            if url:
                webbrowser.open(url)
        b = ttk.Button(parent, text=label, command=go)
        b.pack(anchor="w", pady=(0, 6))
        return b

    def entry_row(parent, label, var, width=34, browse=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=14).pack(side="left")
        ttk.Entry(row, textvariable=var, width=width).pack(side="left", fill="x", expand=True)
        if browse:
            ttk.Button(row, text="찾아보기", command=browse).pack(side="left", padx=(6, 0))
        return row

    # ---- pages: each returns a validate() -> bool -------------------------
    def page_source():
        text(body, "내 글이 어디에 있나요?", strong=True)
        ttk.Radiobutton(body, text="도쿠위키(DokuWiki)에 쓴 글", value="dokuwiki",
                        variable=v["source"], command=lambda: refresh_source()).pack(anchor="w")
        ttk.Radiobutton(body, text="그냥 마크다운(.md) 파일로 쓴 글 (옵시디언 등)", value="markdown",
                        variable=v["source"], command=lambda: refresh_source()).pack(anchor="w", pady=(0, 10))
        hint = text(body, "", pady=(0, 6))

        def pick():
            d = filedialog.askdirectory(initialdir=v["folder"].get() or None)
            if d:
                v["folder"].set(os.path.normpath(d))
        entry_row(body, "글이 든 폴더", v["folder"], browse=pick)

        def refresh_source():
            if v["source"].get() == "dokuwiki":
                s = ("도쿠위키 폴더 안에서, 책으로 만들 .txt 파일이 들어 있는 폴더를 고르세요.\n"
                     "(.txt 파일 하나가 책 한 권이 됩니다. 예: …\\dokuwiki\\data\\pages\\내책들)")
            else:
                s = ("폴더 하나를 고르세요. 그 안의 하위 폴더 하나가 책 한 권이 되고,\n"
                     "책 폴더 안의 폴더는 장, 그 안의 .md 파일은 글이 됩니다.")
            hint.set_text(s)
        refresh_source()

        def validate():
            f = v["folder"].get().strip()
            if not f or not os.path.isdir(f):
                messagebox.showerror("폴더", "폴더를 찾을 수 없습니다. [찾아보기]로 골라 주세요.")
                return False
            return True
        return validate

    def page_tools():
        text(body, "필요한 프로그램이 깔려 있는지 확인합니다.", strong=True)
        git_ok = bool(shutil.which("git"))
        text(body, ("✔ git 이 설치되어 있습니다." if git_ok else
                    "✘ git 이 없습니다. 글을 GitHub에 올리는 데 꼭 필요합니다."), pady=(0, 2))
        if not git_ok:
            open_btn(body, "git 설치 페이지 열기 (설치 후 이 창을 다시 여세요)",
                     lambda: "https://git-scm.com/download/win")
        if v["source"].get() == "dokuwiki":
            pandoc = config.find_pandoc(local["pandoc"])
            text(body, ("✔ pandoc 이 설치되어 있습니다." if pandoc else
                        "✘ pandoc 이 없습니다. 도쿠위키 글을 바꾸는 데 필요합니다.\n"
                        "   설치 후 이 창을 다시 여세요. (명령 프롬프트에서  winget install pandoc)"),
                 pady=(8, 2))
            if not pandoc:
                open_btn(body, "pandoc 설치 페이지 열기", lambda: "https://pandoc.org/installing.html")
            v["pandoc"] = pandoc
        else:
            v["pandoc"] = local["pandoc"]

        if git_ok and not (v["git_name"].get() and v["git_email"].get()):
            text(body, "git 이 '누가 올렸는지' 알아야 합니다. 이름과 이메일을 한 번만 적어 주세요.\n"
                       "(아무 이름이나 괜찮고, GitHub 가입 이메일이면 더 좋습니다.)", pady=(14, 4))
            entry_row(body, "이름", v["git_name"])
            entry_row(body, "이메일", v["git_email"])

        def validate():
            if not git_ok:
                return messagebox.askyesno("git", "git 이 없으면 GitHub에 올릴 수 없습니다.\n그래도 계속할까요?")
            name, email = v["git_name"].get().strip(), v["git_email"].get().strip()
            if name and email:
                if git_config_get("user.name") != name:
                    subprocess.run(["git", "config", "--global", "user.name", name])
                if git_config_get("user.email") != email:
                    subprocess.run(["git", "config", "--global", "user.email", email])
            elif not git_config_get("user.name"):
                messagebox.showerror("git", "이름과 이메일을 모두 적어 주세요.")
                return False
            return True
        return validate

    def page_github():
        text(body, "GitHub에 내 사이트 저장소를 만듭니다.", strong=True)
        text(body, "① GitHub 계정이 없다면 먼저 가입하세요.", pady=(0, 2))
        open_btn(body, "GitHub 가입 페이지 열기", lambda: "https://github.com/signup")
        text(body, "② GitHub 아이디(로그인할 때의 이름)를 적으세요.", pady=(0, 2))
        entry_row(body, "GitHub 아이디", v["user"], width=24)

        def mark_touched(*_):
            # only a hand edit counts; our own auto-fill must not
            if not repo_touched.get("auto"):
                repo_touched["v"] = v["repo"].get() != (v["user"].get().strip() + ".github.io")
        repo_row = entry_row(body, "저장소 이름", v["repo"], width=34)
        v["repo"].trace_add("write", mark_touched)
        text(body, "저장소 이름은 보통 그대로 두세요. 아이디.github.io 로 만들면 사이트 주소가\n"
                   "https://아이디.github.io 가 됩니다.", pady=(0, 6))

        def new_url():
            u, r = v["user"].get().strip(), v["repo"].get().strip()
            if not u or not r:
                messagebox.showerror("저장소", "GitHub 아이디부터 적어 주세요.")
                return None
            return "https://github.com/new?name=" + r
        text(body, "③ 저장소를 만드세요. 열리는 화면에서 이름은 이미 채워져 있습니다.\n"
                   "   'Public'을 고르고, 'Add a README' 같은 체크는 모두 끈 채로 Create repository.", pady=(0, 2))
        open_btn(body, "저장소 만드는 페이지 열기", new_url)

        def pages_url():
            u, r = v["user"].get().strip(), v["repo"].get().strip()
            return "https://github.com/%s/%s/settings/pages" % (u, r) if u and r else None
        text(body, "④ 열리는 화면의 Build and deployment → Source 를 'GitHub Actions'로 바꾸세요.", pady=(0, 2))
        open_btn(body, "Pages 설정 페이지 열기", pages_url)

        result = text(body, "", pady=(4, 0))

        def verify():
            kind, msg = remote_check.check(
                remote_check.make_url(v["user"].get(), v["repo"].get()), "main")
            icon = {"ok": "✔ ", "warn": "△ ", "error": "✘ "}[kind]
            result.set_text(icon + msg)
        ttk.Button(body, text="⑤ 연결 확인", command=verify).pack(anchor="w", pady=(4, 0))

        def validate():
            if not v["user"].get().strip() or not v["repo"].get().strip():
                messagebox.showerror("GitHub", "GitHub 아이디를 적어 주세요.")
                return False
            return True
        return validate

    def page_site():
        text(body, "사이트에 보일 이름을 정하세요. (나중에 바꿀 수 있습니다)", strong=True)
        entry_row(body, "사이트 제목", v["title"], width=40)
        entry_row(body, "한 줄 소개", v["tagline"], width=40)
        text(body, "댓글창은 나중에 [설정]의 '댓글' 항목에서 켤 수 있습니다.", pady=(12, 0))
        return lambda: True

    def page_done():
        text(body, "준비가 끝났습니다!", strong=True)
        url = remote_check.make_url(v["user"].get(), v["repo"].get())
        text(body, "[마침]을 누르면 설정이 저장됩니다.\n\n"
                   "그다음 열리는 창에서 [사이트에 올리기]를 누르면 글을 변환해서 GitHub에 올립니다.\n"
                   "처음 올릴 때 git 이 브라우저로 GitHub 로그인을 물어보면 로그인하세요.\n\n"
                   "올린 뒤 1~2분이면 아래 주소에 사이트가 나타납니다.")
        text(body, "https://%s/" % v["repo"].get().strip(), pady=(0, 6))
        text(body, "(저장소 주소: %s)" % url)
        return lambda: True

    pages = [("1 / 5  글이 있는 곳", page_source), ("2 / 5  프로그램 확인", page_tools),
             ("3 / 5  GitHub 준비", page_github), ("4 / 5  사이트 이름", page_site),
             ("5 / 5  끝", page_done)]
    state = {"i": 0, "validate": None}

    def save():
        use_doku = v["source"].get() == "dokuwiki"
        folder = os.path.normpath(v["folder"].get().strip())
        new = dict(local)
        new.update({
            "use_dokuwiki": use_doku,
            "use_markdown": not use_doku,
            "books_dir": folder if use_doku else local["books_dir"],
            "markdown_dir": folder if not use_doku else local["markdown_dir"],
            "pandoc": v.get("pandoc", local["pandoc"]) if isinstance(v.get("pandoc"), str) else local["pandoc"],
            "git_remote": remote_check.make_url(v["user"].get(), v["repo"].get()),
            "git_branch": local["git_branch"] or "main",
            "auto_push": True,
        })
        config.save_local(new)
        s = dict(site)
        s["title"] = v["title"].get().strip() or config.DEFAULT_SITE["title"]
        s["tagline"] = v["tagline"].get().strip()
        config.save_site(s)
        saved["ok"] = True
        root.destroy()

    def show(i):
        state["i"] = i
        for w in body.winfo_children():
            w.destroy()
        title, builder = pages[i]
        head.configure(text=title)
        state["validate"] = builder()
        back_btn.state(["!disabled"] if i > 0 else ["disabled"])
        last = i == len(pages) - 1
        next_btn.configure(text="마침" if last else "다음 →")

    def go_next():
        if not state["validate"]():
            return
        if state["i"] == len(pages) - 1:
            save()
        else:
            show(state["i"] + 1)

    def go_back():
        if state["i"] > 0:
            show(state["i"] - 1)

    next_btn.configure(command=go_next)
    back_btn.configure(command=go_back)
    show(0)
    root.mainloop()
    return saved["ok"]


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
