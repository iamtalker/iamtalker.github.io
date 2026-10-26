#!/usr/bin/env python3
"""Settings window: fill in the form instead of editing text files.

Saves config.json (this PC's paths) and site.json (site title etc.).
Opened from the [설정] button of app.py (update.bat); on first use it shows the wizard.
"""
import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import remote_check  # noqa: E402


def clean_repo(text):
    """'owner/name' from a pasted repo, clone URL or browser URL."""
    return re.sub(r"(^https?://github\.com/|\.git$|/$)", "", text.strip())


def main():
    # first run (no config.json yet): the step-by-step wizard instead of the full form
    if not os.path.exists(config.CONFIG_PATH) and "--full" not in sys.argv:
        import wizard
        wizard.run()
        return

    local = config.load_local()
    site = config.load_site()

    root = tk.Tk()
    root.title("사이트 설정")
    # the form scrolls inside a canvas; the save/cancel bar stays fixed below it
    canvas = tk.Canvas(root, highlightthickness=0)
    vbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vbar.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    vbar.grid(row=0, column=1, sticky="ns")
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    frm = ttk.Frame(canvas, padding=16)
    frm_id = canvas.create_window((0, 0), window=frm, anchor="nw")
    frm.columnconfigure(1, weight=1)
    frm.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(frm_id, width=e.width))
    root.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(
        -1 if e.delta > 0 else 1, "units") if frm.winfo_reqheight() > canvas.winfo_height() else None)

    vars_ = {
        "use_dokuwiki": tk.BooleanVar(value=local["use_dokuwiki"]),
        "use_markdown": tk.BooleanVar(value=local["use_markdown"]),
        "markdown_dir": tk.StringVar(value=local["markdown_dir"]),
        "books_dir": tk.StringVar(value=local["books_dir"]),
        "media_dir": tk.StringVar(value=local["media_dir"]),
        "pandoc": tk.StringVar(value=local["pandoc"] or config.find_pandoc()),
        "title": tk.StringVar(value=site["title"]),
        "tagline": tk.StringVar(value=site["tagline"]),
        "description": tk.StringVar(value=site["description"]),
        "lang": tk.StringVar(value=site["lang"]),
        "auto_push": tk.BooleanVar(value=local["auto_push"]),
        "git_remote": tk.StringVar(value=local["git_remote"]),
        "git_branch": tk.StringVar(value=local["git_branch"]),
        "commit_message": tk.StringVar(value=local["commit_message"]),
        "g_repo": tk.StringVar(value=site["giscus"].get("repo", "")),
        "g_repoId": tk.StringVar(value=site["giscus"].get("repoId", "")),
        "g_category": tk.StringVar(value=site["giscus"].get("category", "")),
        "g_categoryId": tk.StringVar(value=site["giscus"].get("categoryId", "")),
    }

    row = 0

    bg = ttk.Style().lookup("TFrame", "background") or root.cget("bg")
    note_font = tkfont.nametofont("TkDefaultFont")

    def note(text, pady=(0, 4)):
        """Help text in a read-only Text so it can be selected and copied."""
        nonlocal row
        t = tk.Text(frm, height=1, width=52, wrap="word", relief="flat", borderwidth=0,
                    highlightthickness=0, background=bg, foreground="#666",
                    font=note_font, cursor="xterm")
        t.insert("1.0", text)

        def fit(_e=None):
            n = t.count("1.0", "end-1c", "displaylines")
            t.configure(height=max(1, n[0] if n else 1))

        def block(e):
            # keep selection and Ctrl+C / Ctrl+A, refuse any editing
            if (e.state & 0x4) and e.keysym.lower() in ("c", "a"):
                return None
            if e.keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
                return None
            return "break"

        t.bind("<Key>", block)
        t.bind("<Configure>", fit)
        t.bind("<Button-1>", lambda e: t.focus_set())
        t.grid(row=row, column=1, sticky="ew", pady=pady)
        row += 1

    def section(text):
        nonlocal row
        ttk.Label(frm, text=text, font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(10 if row else 0, 4))
        row += 1

    def field(label, key, browse=None, hint=None):
        nonlocal row
        ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(frm, textvariable=vars_[key], width=52).grid(
            row=row, column=1, pady=2, sticky="ew")
        if browse:
            ttk.Button(frm, text="찾아보기", command=browse).grid(row=row, column=2, padx=(6, 0))
        row += 1
        if hint:
            note(hint)

    def pick_dir(key):
        def run():
            d = filedialog.askdirectory(initialdir=vars_[key].get() or None)
            if d:
                vars_[key].set(os.path.normpath(d))
        return run

    def pick_file(key):
        def run():
            f = filedialog.askopenfilename(
                filetypes=[("pandoc", "pandoc*"), ("All files", "*.*")])
            if f:
                vars_[key].set(os.path.normpath(f))
        return run

    section("입력 소스 (둘 다 켜면 함께 빌드)")
    ttk.Checkbutton(
        frm, text="도쿠위키 → 마크다운", variable=vars_["use_dokuwiki"],
    ).grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1
    ttk.Checkbutton(
        frm, text="마크다운 → 마크다운", variable=vars_["use_markdown"],
    ).grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1

    section("마크다운 소스")
    field("마크다운 폴더", "markdown_dir", pick_dir("markdown_dir"),
          "이 폴더 안의 하위 폴더 하나 = 책 하나 (그 안의 폴더 = 장, .md = 글)")

    section("도쿠위키 소스")
    field("책 폴더", "books_dir", pick_dir("books_dir"),
          "책 .txt 파일이 들어 있는 도쿠위키 폴더 (.txt 하나 = 책 하나).\n"
          "예: C:\\DokuWiki\\data\\pages\\내책들\n"
          "'pages' 폴더는 이 경로에서 자동으로 찾습니다.")
    field("미디어 폴더 (선택)", "media_dir", pick_dir("media_dir"),
          "비워두면 pages 폴더 옆의 media 폴더를 자동으로 씁니다.")
    field("pandoc 경로", "pandoc", pick_file("pandoc"),
          "비워두면 PATH에서 자동 검색")

    section("사이트 정보")
    field("사이트 제목", "title")
    field("한 줄 소개", "tagline")
    field("설명", "description")
    field("언어 코드", "lang", None, "예: ko-KR, en-US")

    section("댓글 (giscus, 선택)")

    def repo_from_remote():
        m = re.match(r"https?://github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?/?$",
                     vars_["git_remote"].get().strip())
        return m.group(1) if m else ""

    def open_url(url):
        return lambda: webbrowser.open(url)

    def open_repo_page(suffix):
        def run():
            repo = clean_repo(vars_["g_repo"].get()) or repo_from_remote()
            if not repo:
                messagebox.showerror("댓글", "먼저 아래 '댓글 저장소' 칸에 아이디/저장소이름을 쓰세요.\n"
                                     "(GitHub 업로드의 저장소 주소를 먼저 넣었다면 자동으로 채워 줍니다.)")
                return
            webbrowser.open("https://github.com/%s%s" % (repo, suffix))
        return run

    note("① GitHub에서 아래 두 가지를 한 번만 해 두세요", pady=0)
    steps = ttk.Frame(frm)
    steps.grid(row=row, column=1, sticky="w", pady=(2, 6))
    ttk.Button(steps, text="giscus 앱 설치 페이지 열기",
               command=open_url("https://github.com/apps/giscus")).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(steps, text="Discussions 켜는 페이지 열기",
               command=open_repo_page("/settings#features")).grid(row=0, column=1)
    row += 1
    note("설치 화면에서 'Only select repositories'를 고르고 내 사이트 저장소를 선택하세요.\n"
         "Discussions 화면에서는 Features 항목의 Discussions 체크를 켭니다.", pady=(0, 6))

    example = repo_from_remote() or "myname/myname.github.io"
    note("② giscus.app 에서 코드를 만들어 아래에 통째로 붙여넣고 [값 자동 입력]을 누르세요\n"
         "giscus.app 의 '저장소' 칸에는 이렇게 쓰세요:  %s\n"
         "(https://github.com/ 나 .git 을 붙이지 않고, 아이디/저장소이름 만 씁니다)" % example, pady=0)
    paste = tk.Text(frm, height=4, width=52)
    paste.grid(row=row, column=1, sticky="ew", pady=2)
    row += 1

    def fill_from_paste():
        text = paste.get("1.0", "end")
        found = {}
        for attr in ("repo", "repo-id", "category", "category-id"):
            m = re.search(r'data-%s\s*=\s*"([^"]*)"' % attr, text)
            if m:
                found[attr] = m.group(1).strip()
        if "repo-id" not in found or "category-id" not in found:
            messagebox.showwarning(
                "댓글", "붙여넣은 내용에서 data-repo-id / data-category-id 를 찾지 못했습니다.\n"
                "giscus.app 맨 아래 '<script src=\"https://giscus.app/client.js\" …' 코드 전체를 복사해 주세요.")
            return
        if "repo" in found:
            vars_["g_repo"].set(clean_repo(found["repo"]))
        elif not vars_["g_repo"].get().strip():
            vars_["g_repo"].set(repo_from_remote())
        vars_["g_repoId"].set(found["repo-id"])
        vars_["g_categoryId"].set(found["category-id"])
        if "category" in found:
            vars_["g_category"].set(found["category"])
        messagebox.showinfo("댓글", "repo ID와 카테고리 ID를 채웠습니다.")

    bar = ttk.Frame(frm)
    bar.grid(row=row, column=1, sticky="w", pady=(0, 6))
    ttk.Button(bar, text="giscus.app 열기",
               command=open_url("https://giscus.app/ko")).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(bar, text="값 자동 입력", command=fill_from_paste).grid(row=0, column=1)
    row += 1

    field("댓글 저장소", "g_repo", None,
          "댓글이 저장될 GitHub 저장소를 '내GitHub아이디/저장소이름' 형태로 씁니다.\n"
          "(업로드용 '저장소 주소'와 달리 https://github.com/ 와 .git 은 붙이지 않습니다.)\n"
          "예: myname/myname.github.io  (공개 저장소여야 하고, 저장소 Settings에서\n"
          "Discussions를 켜고 giscus 앱을 설치해야 합니다.) 비워두면 댓글창이 없습니다.")
    field("repo ID", "g_repoId", None,
          "https://giscus.app 에서 위 저장소를 입력하면 아래쪽에 나오는\n"
          "data-repo-id 값을 복사해 붙여넣으세요. (R_ 로 시작)")
    field("카테고리", "g_category", None,
          "댓글이 모일 Discussions 카테고리 이름. 보통 Announcements")
    field("카테고리 ID", "g_categoryId", None,
          "giscus.app 에서 카테고리를 고르면 나오는 data-category-id 값 (DIC_ 로 시작)")

    section("GitHub 업로드")

    def check_remote():
        kind, msg = remote_check.check(
            vars_["git_remote"].get(), vars_["git_branch"].get())
        show = {"ok": messagebox.showinfo, "warn": messagebox.showwarning,
                "error": messagebox.showerror}[kind]
        show("연결 확인", msg)

    field("저장소 주소", "git_remote", check_remote,
          "GitHub에서 만든 저장소 페이지의 초록색 'Code' 버튼 → HTTPS 탭에 나오는 주소를\n"
          "그대로 복사해 붙여넣으세요. 형태: https://github.com/내GitHub아이디/저장소이름.git\n"
          "예: https://github.com/myname/myname.github.io.git\n"
          "(저장소 이름을 '내GitHub아이디.github.io'로 만들면 사이트 주소가\n"
          "https://내GitHub아이디.github.io 가 됩니다. 오른쪽 버튼 = 연결 확인)")
    field("브랜치", "git_branch", None, "GitHub Pages가 배포에 쓰는 브랜치 (보통 main)")
    field("커밋 메시지", "commit_message")
    note("로그인 정보(비밀번호/토큰)는 이 프로그램이 저장하지 않고 git 이 관리합니다.")
    ttk.Checkbutton(
        frm, text="변환 후 GitHub 에 자동 업로드 ([사이트에 올리기])",
        variable=vars_["auto_push"],
    ).grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1

    def save():
        books = vars_["books_dir"].get().strip()
        md_dir = vars_["markdown_dir"].get().strip()
        use_doku = bool(vars_["use_dokuwiki"].get())
        use_md = bool(vars_["use_markdown"].get())
        if not (use_doku or use_md):
            messagebox.showerror("설정", "입력 소스를 하나 이상 선택하세요.")
            return
        if use_md and not os.path.isdir(md_dir):
            messagebox.showerror("설정", "마크다운 폴더를 찾을 수 없습니다.")
            return
        pandoc = vars_["pandoc"].get().strip()
        if use_doku:
            if not books:
                messagebox.showerror("설정", "책 폴더를 입력하세요.")
                return
            if not os.path.isdir(books):
                if not messagebox.askyesno(
                        "설정", "'%s' 폴더가 아직 없습니다.\n새로 만들까요?" % books):
                    return
                os.makedirs(books, exist_ok=True)
            if not config.find_pandoc(pandoc):
                messagebox.showwarning(
                    "설정", "pandoc을 찾을 수 없습니다. 설치 후 경로를 지정해야 빌드됩니다.")
        config.save_local({
            "use_dokuwiki": use_doku,
            "use_markdown": use_md,
            "markdown_dir": os.path.normpath(md_dir) if md_dir else "",
            "books_dir": os.path.normpath(books) if books else "",
            "media_dir": vars_["media_dir"].get().strip(),
            "pandoc": pandoc,
            "auto_push": bool(vars_["auto_push"].get()),
            "git_remote": vars_["git_remote"].get().strip(),
            "git_branch": vars_["git_branch"].get().strip() or "main",
            "commit_message": vars_["commit_message"].get().strip() or "content update",
        })
        config.save_site({
            "title": vars_["title"].get().strip() or config.DEFAULT_SITE["title"],
            "tagline": vars_["tagline"].get().strip(),
            "description": vars_["description"].get().strip(),
            "lang": vars_["lang"].get().strip() or config.DEFAULT_SITE["lang"],
            "giscus": {
                "repo": clean_repo(vars_["g_repo"].get()),
                "repoId": vars_["g_repoId"].get().strip(),
                "category": vars_["g_category"].get().strip() or "Announcements",
                "categoryId": vars_["g_categoryId"].get().strip(),
            },
        })
        messagebox.showinfo("설정", "저장했습니다.")
        root.destroy()

    btns = ttk.Frame(root, padding=(16, 8))
    btns.grid(row=1, column=0, columnspan=2, sticky="e")
    def rerun_wizard():
        root.destroy()
        import wizard
        wizard.run()
    ttk.Button(btns, text="처음 설정 마법사", command=rerun_wizard).grid(row=0, column=2, padx=(24, 0))
    ttk.Button(btns, text="취소", command=root.destroy).grid(row=0, column=0, padx=6)
    ttk.Button(btns, text="저장", command=save).grid(row=0, column=1)

    root.update_idletasks()
    canvas.configure(
        width=frm.winfo_reqwidth(),
        height=min(frm.winfo_reqheight(), int(root.winfo_screenheight() * 0.8)))

    root.mainloop()


if __name__ == "__main__":
    main()
