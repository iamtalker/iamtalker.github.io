#!/usr/bin/env python3
"""Settings window: fill in the form instead of editing text files.

Saves config.json (this PC's paths) and site.json (site title etc.).
Run it with settings.bat; update.bat opens it automatically on first use.
"""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def main():
    local = config.load_local()
    site = config.load_site()

    root = tk.Tk()
    root.title("사이트 설정")
    root.resizable(False, False)
    frm = ttk.Frame(root, padding=16)
    frm.grid()

    vars_ = {
        "use_dokuwiki": tk.BooleanVar(value=local["use_dokuwiki"]),
        "use_markdown": tk.BooleanVar(value=local["use_markdown"]),
        "markdown_dir": tk.StringVar(value=local["markdown_dir"]),
        "pages_dir": tk.StringVar(value=local["pages_dir"]),
        "books_subdir": tk.StringVar(value=local["books_subdir"]),
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

    def section(text):
        nonlocal row
        ttk.Label(frm, text=text, font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(10 if row else 0, 4))
        row += 1

    def field(label, key, browse=None, hint=None):
        nonlocal row
        ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(frm, textvariable=vars_[key], width=52).grid(row=row, column=1, pady=2)
        if browse:
            ttk.Button(frm, text="찾아보기", command=browse).grid(row=row, column=2, padx=(6, 0))
        row += 1
        if hint:
            ttk.Label(frm, text=hint, foreground="#666").grid(
                row=row, column=1, sticky="w", pady=(0, 4))
            row += 1

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
    field("도쿠위키 pages 폴더", "pages_dir", pick_dir("pages_dir"),
          "예: …\\dokuwiki\\data\\pages")
    field("책 폴더 이름", "books_subdir", None,
          "pages 폴더 안에서 .txt 파일 하나 = 책 하나인 폴더")
    field("미디어 폴더 (선택)", "media_dir", pick_dir("media_dir"),
          "비워두면 pages 옆의 media 폴더를 자동 사용")
    field("pandoc 경로", "pandoc", pick_file("pandoc"),
          "비워두면 PATH에서 자동 검색")

    section("사이트 정보")
    field("사이트 제목", "title")
    field("한 줄 소개", "tagline")
    field("설명", "description")
    field("언어 코드", "lang", None, "예: ko-KR, en-US")

    section("댓글 (giscus, 선택)")
    field("저장소", "g_repo", None, "예: 아이디/아이디.github.io — 비워두면 댓글창 없음")
    field("repo ID", "g_repoId", None, "giscus.app 에서 발급되는 값")
    field("카테고리", "g_category")
    field("카테고리 ID", "g_categoryId")

    section("GitHub 업로드")

    def check_remote():
        url = vars_["git_remote"].get().strip()
        if not url:
            messagebox.showerror("연결 확인", "저장소 주소를 입력하세요.")
            return
        if not shutil.which("git"):
            messagebox.showerror("연결 확인", "git이 설치되어 있지 않습니다.")
            return
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            r = subprocess.run(
                ["git", "ls-remote", "--heads", url], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30, env=env)
        except subprocess.TimeoutExpired:
            messagebox.showerror("연결 확인", "30초 안에 응답이 없습니다.")
            return
        if r.returncode == 0:
            messagebox.showinfo("연결 확인", "저장소에 접근할 수 있습니다.")
        else:
            messagebox.showwarning(
                "연결 확인",
                "접근하지 못했습니다. 주소가 틀렸거나, 비공개 저장소라 아직 로그인 전일 수 있습니다.\n"
                "(로그인은 첫 업로드 때 git이 브라우저로 물어봅니다.)\n\n" + r.stderr.strip())

    field("저장소 주소", "git_remote", check_remote,
          "예: https://github.com/아이디/아이디.github.io.git  (오른쪽 버튼 = 연결 확인)")
    field("브랜치", "git_branch", None, "GitHub Pages가 배포에 쓰는 브랜치 (보통 main)")
    field("커밋 메시지", "commit_message")
    ttk.Label(frm, text="로그인 정보(비밀번호/토큰)는 이 프로그램이 저장하지 않고 git 이 관리합니다.",
              foreground="#666").grid(row=row, column=1, sticky="w", pady=(0, 4))
    row += 1
    ttk.Checkbutton(
        frm, text="빌드 후 GitHub 에 자동 업로드 (update.bat)",
        variable=vars_["auto_push"],
    ).grid(row=row, column=0, columnspan=3, sticky="w")
    row += 1

    def save():
        pages = vars_["pages_dir"].get().strip()
        books = vars_["books_subdir"].get().strip()
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
            if not pages or not os.path.isdir(pages):
                messagebox.showerror("설정", "도쿠위키 pages 폴더를 찾을 수 없습니다.")
                return
            if not books:
                messagebox.showerror("설정", "책 폴더 이름을 입력하세요.")
                return
            if not os.path.isdir(os.path.join(pages, books)):
                if not messagebox.askyesno(
                        "설정", "pages 안에 '%s' 폴더가 아직 없습니다.\n새로 만들까요?" % books):
                    return
                os.makedirs(os.path.join(pages, books), exist_ok=True)
            if not config.find_pandoc(pandoc):
                messagebox.showwarning(
                    "설정", "pandoc을 찾을 수 없습니다. 설치 후 경로를 지정해야 빌드됩니다.")
        config.save_local({
            "use_dokuwiki": use_doku,
            "use_markdown": use_md,
            "markdown_dir": os.path.normpath(md_dir) if md_dir else "",
            "pages_dir": os.path.normpath(pages) if pages else "",
            "books_subdir": books,
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
                "repo": vars_["g_repo"].get().strip(),
                "repoId": vars_["g_repoId"].get().strip(),
                "category": vars_["g_category"].get().strip() or "Announcements",
                "categoryId": vars_["g_categoryId"].get().strip(),
            },
        })
        messagebox.showinfo("설정", "저장했습니다.")
        root.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=row, column=0, columnspan=3, sticky="e", pady=(14, 0))
    ttk.Button(btns, text="취소", command=root.destroy).grid(row=0, column=0, padx=6)
    ttk.Button(btns, text="저장", command=save).grid(row=0, column=1)

    root.mainloop()


if __name__ == "__main__":
    main()
