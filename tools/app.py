#!/usr/bin/env python3
"""Main window - the one thing to open.

  [사이트에 올리기]  convert the books, then commit + push (what update.bat used to do)
  [설정]            the settings window (first run: the step-by-step wizard)

The build scripts run as child processes and their output is shown in the log
box. publish.py asks its one question (overwrite what is on GitHub?) through
a marker line, which this window turns into a dialog.
"""
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import messagebox, ttk

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import config  # noqa: E402

ROOT = config.REPO_ROOT
ASK = "@@ASK@@"
NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW: no console flashing up for child processes


def python_exe():
    exe = sys.executable
    d, name = os.path.split(exe)
    if name.lower() == "pythonw.exe":
        cand = os.path.join(d, "python.exe")
        if os.path.exists(cand):
            return cand
    return exe


def site_urls(remote):
    """(site address, GitHub Actions page) from the repository URL."""
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", remote.strip())
    if not m:
        return "", ""
    user, repo = m.groups()
    if repo.lower().endswith(".github.io"):
        site = "https://%s/" % repo
    else:
        site = "https://%s.github.io/%s/" % (user, repo)
    return site, "https://github.com/%s/%s/actions" % (user, repo)


def run_settings():
    subprocess.run([python_exe(), os.path.join(TOOLS, "settings_gui.py")], cwd=ROOT,
                   creationflags=NO_WINDOW)


def main():
    if not os.path.exists(config.CONFIG_PATH):
        run_settings()          # wizard
        if not os.path.exists(config.CONFIG_PATH):
            return

    root = tk.Tk()
    root.title("책 사이트 도우미")
    root.geometry("760x560")
    root.minsize(560, 420)

    bg = ttk.Style().lookup("TFrame", "background") or root.cget("bg")
    q = queue.Queue()
    state = {"proc": None, "busy": False}

    top = ttk.Frame(root, padding=(16, 14, 16, 6))
    top.pack(fill="x")
    summary = ttk.Label(top, justify="left")
    summary.pack(anchor="w")

    btns = ttk.Frame(root, padding=(16, 4))
    btns.pack(fill="x")
    upload_btn = ttk.Button(btns, text="▶ 사이트에 올리기")
    upload_btn.pack(side="left")
    settings_btn = ttk.Button(btns, text="설정")
    settings_btn.pack(side="left", padx=(8, 0))
    reset_btn = ttk.Button(btns, text="설정 초기화")
    reset_btn.pack(side="left", padx=(8, 0))
    site_btn = ttk.Button(btns, text="내 사이트 열기")
    site_btn.pack(side="right")
    actions_btn = ttk.Button(btns, text="올라가는 중인지 보기")
    actions_btn.pack(side="right", padx=(0, 8))

    status = ttk.Label(root, padding=(16, 6, 16, 2), font=("", 10, "bold"))
    status.pack(fill="x")

    logf = ttk.Frame(root, padding=(16, 0, 16, 14))
    logf.pack(fill="both", expand=True)
    log = tk.Text(logf, wrap="word", height=10, relief="solid", borderwidth=1,
                  font=tkfont.nametofont("TkFixedFont"), background="white")
    sb = ttk.Scrollbar(logf, command=log.yview)
    log.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    log.pack(side="left", fill="both", expand=True)

    def block(e):  # selectable / copyable, not editable
        if (e.state & 0x4) and e.keysym.lower() in ("c", "a"):
            return None
        if e.keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
            return None
        return "break"
    log.bind("<Key>", block)

    def put(s):
        log.insert("end", s)
        log.see("end")

    def refresh():
        local, site = config.load_local(), config.load_site()
        src = local["books_dir"] if local["use_dokuwiki"] else local["markdown_dir"]
        site_url, _ = site_urls(local["git_remote"])
        summary.configure(text="사이트: %s\n글이 있는 곳: %s\n올릴 곳: %s" % (
            site["title"] or "(제목 없음)", src or "(미설정)", site_url or "(저장소 주소 미설정)"))

    def set_busy(busy):
        state["busy"] = busy
        for b in (upload_btn, settings_btn, reset_btn):
            b.state(["disabled"] if busy else ["!disabled"])

    def pipeline(local):
        steps = [("글을 사이트로 변환", ["build_books.py", "docs"]),
                 ("첫 페이지 만들기", ["build_library.py"])]
        if local["auto_push"]:
            steps.append(("GitHub에 올리기", ["publish.py"]))
        return steps

    def worker(steps):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", BOOK_GUI="1")
        for title, args in steps:
            q.put(("log", "\n=== %s ===\n" % title))
            p = subprocess.Popen(
                [python_exe(), "-u", os.path.join(TOOLS, args[0])] + args[1:], cwd=ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", env=env, creationflags=NO_WINDOW)
            state["proc"] = p
            for line in p.stdout:
                if line.startswith(ASK):
                    q.put(("ask", json.loads(line[len(ASK):])))
                else:
                    q.put(("log", line))
            if p.wait() != 0:
                q.put(("done", False))
                return
        q.put(("done", True))

    def poll():
        try:
            while True:
                kind, val = q.get_nowait()
                if kind == "log":
                    put(val)
                elif kind == "settings_done":
                    after_settings()
                elif kind == "ask":
                    ans = messagebox.askyesno("확인", val, icon="warning")
                    p = state["proc"]
                    p.stdin.write("y\n" if ans else "n\n")
                    p.stdin.flush()
                elif kind == "done":
                    set_busy(False)
                    local = config.load_local()
                    if val and local["auto_push"]:
                        site_url, _ = site_urls(local["git_remote"])
                        status.configure(text="✔ 올렸습니다. 1~2분 뒤 사이트에 반영됩니다.", foreground="#1a7f37")
                        put("\n완료. 1~2분 뒤 %s 에서 확인하세요.\n" % (site_url or "사이트"))
                    elif val:
                        status.configure(text="✔ 변환만 끝났습니다. (자동 업로드가 꺼져 있어 올리지 않았습니다)",
                                         foreground="#1a7f37")
                    else:
                        status.configure(text="✘ 실패했습니다. 아래 로그의 마지막 메시지를 확인하세요.",
                                         foreground="#b42318")
        except queue.Empty:
            pass
        root.after(100, poll)

    def start_upload():
        if state["busy"]:
            return
        local = config.load_local()
        problems = []
        src = local["books_dir"] if local["use_dokuwiki"] else local["markdown_dir"]
        if not src or not os.path.isdir(src):
            problems.append("글이 있는 폴더를 찾을 수 없습니다. [설정]에서 확인하세요.")
        if local["auto_push"] and not local["git_remote"].strip():
            problems.append("GitHub 저장소 주소가 비어 있습니다. [설정]에서 입력하세요.")
        if problems:
            messagebox.showerror("준비가 덜 됐습니다", "\n".join(problems))
            return
        log.delete("1.0", "end")
        status.configure(text="진행 중…", foreground="#444")
        set_busy(True)
        threading.Thread(target=worker, args=(pipeline(local),), daemon=True).start()

    def open_settings():
        set_busy(True)

        def run():
            run_settings()
            q.put(("settings_done", None))   # the UI is only touched from poll()
        threading.Thread(target=run, daemon=True).start()

    def after_settings():
        refresh()
        set_busy(False)

    def reset_settings():
        if state["busy"]:
            return
        if not messagebox.askyesno(
                "설정 초기화",
                "설정을 처음 상태로 되돌립니다.\n\n"
                "• 이 컴퓨터 설정: 글 폴더, GitHub 저장소 주소, pandoc 경로\n"
                "• 사이트 정보: 제목, 소개, 댓글 설정\n\n"
                "올려 둔 사이트와 내 글 원본은 그대로입니다. 단, 다음에 [사이트에 올리기]를 하면\n"
                "초기화된 사이트 정보(제목 등)로 올라갑니다.\n"
                "지금 설정은 .settings_backup 폴더에 백업해 둡니다.\n\n계속할까요?",
                icon="warning"):
            return
        backup = os.path.join(ROOT, ".settings_backup", time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(backup, exist_ok=True)
        for path in (config.CONFIG_PATH, config.SITE_PATH):
            if os.path.exists(path):
                shutil.copy2(path, backup)
        if os.path.exists(config.CONFIG_PATH):
            os.remove(config.CONFIG_PATH)
        config.save_site(config.DEFAULT_SITE)
        log.delete("1.0", "end")
        put("설정을 초기화했습니다. (백업: %s)\n처음 설정 마법사가 열립니다.\n" % backup)
        status.configure(text="설정 초기화됨", foreground="#444")
        open_settings()   # config.json is gone, so this opens the wizard

    def open_site():
        url, _ = site_urls(config.load_local()["git_remote"])
        if url:
            webbrowser.open(url)

    def open_actions():
        _, url = site_urls(config.load_local()["git_remote"])
        if url:
            webbrowser.open(url)

    upload_btn.configure(command=start_upload)
    settings_btn.configure(command=open_settings)
    reset_btn.configure(command=reset_settings)
    site_btn.configure(command=open_site)
    actions_btn.configure(command=open_actions)

    refresh()
    put("[사이트에 올리기]를 누르면 글을 변환해서 GitHub에 올립니다.\n"
        "처음 올릴 때 git 이 브라우저로 GitHub 로그인을 물어보면 로그인하세요.\n")
    root.after(100, poll)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # pythonw has no console: show the error instead of vanishing
        import traceback
        messagebox.showerror("오류", traceback.format_exc())
