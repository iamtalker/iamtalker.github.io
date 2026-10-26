"""Install the programs this tool needs (git, pandoc) with winget.

install(name, log) runs winget silently, streams its output lines to log(),
then refreshes this process's PATH so shutil.which() finds the new program
without restarting the app. Returns (ok, message).
"""
import os
import shutil
import subprocess
import sys

PACKAGES = {
    "git": "Git.Git",
    "pandoc": "JohnMacFarlane.Pandoc",
}


def have_winget():
    return sys.platform == "win32" and bool(shutil.which("winget"))


def refresh_path():
    """Re-read PATH from the registry (Windows only) and add what is missing."""
    if sys.platform != "win32":
        return
    import winreg
    found = []
    for hive, sub in ((winreg.HKEY_LOCAL_MACHINE,
                       r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(hive, sub) as k:
                found += winreg.QueryValueEx(k, "Path")[0].split(os.pathsep)
        except OSError:
            pass
    have = [p.lower() for p in os.environ.get("PATH", "").split(os.pathsep)]
    extra = [os.path.expandvars(p) for p in found
             if p and os.path.expandvars(p).lower() not in have]
    if extra:
        os.environ["PATH"] = os.pathsep.join([os.environ.get("PATH", "")] + extra)


def install(name, log=print):
    if not have_winget():
        return False, "winget 이 없어 자동 설치를 할 수 없습니다."
    cmd = ["winget", "install", "--id", PACKAGES[name], "-e", "--silent",
           "--accept-package-agreements", "--accept-source-agreements"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in p.stdout:
            line = line.strip()
            # winget draws progress bars with \r / block characters; skip those
            if line and not line.startswith(("-", "\\", "|", "/")) and "█" not in line:
                log(line)
        p.wait()
    except OSError as e:
        return False, "설치를 시작하지 못했습니다: %s" % e
    refresh_path()
    if shutil.which(name):
        return True, "%s 설치가 끝났습니다." % name
    if p.returncode != 0:
        return False, "%s 설치에 실패했습니다 (winget 종료코드 %s)." % (name, p.returncode)
    return False, "%s 설치는 끝났지만 아직 찾지 못했습니다. 이 창을 닫고 다시 여세요." % name
