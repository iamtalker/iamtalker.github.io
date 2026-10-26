"""Small tkinter helpers shared by the wizards.

text()       selectable (copyable) paragraph that grows to fit its text
open_btn()   button that opens a web page
entry_row()  "label  [entry]  [browse]" line
Pager        header + page area + back/next bar; pages are builder functions
"""
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import ttk


def text(parent, s, strong=False, pady=(0, 6)):
    """Read-only Text: can be selected and copied, never edited.

    t.set_text(new) swaps the text and re-fits the height."""
    bg = ttk.Style().lookup("TFrame", "background") or parent.winfo_toplevel().cget("bg")
    t = tk.Text(parent, height=1, width=60, wrap="word", relief="flat", borderwidth=0,
                highlightthickness=0, background=bg, cursor="xterm",
                font=("", 10, "bold") if strong else tkfont.nametofont("TkDefaultFont"),
                foreground="#222" if strong else "#444")
    t.insert("1.0", s)

    def fit(_e=None):
        n = t.count("1.0", "end-1c", "displaylines")
        # count() returns the display-line BREAKS between the two indexes: lines = breaks + 1
        t.configure(height=(n[0] if n else 0) + 1)

    def set_text(new):
        t.delete("1.0", "end")
        t.insert("1.0", new)
        t.update_idletasks()
        fit()

    def block(e):
        if (e.state & 0x4) and e.keysym.lower() in ("c", "a"):
            return None
        if e.keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"):
            return None
        return "break"

    t.set_text = set_text
    t.bind("<Key>", block)
    t.bind("<Configure>", fit)
    t.bind("<Button-1>", lambda e: t.focus_set())
    t.pack(fill="x", pady=pady)
    return t


def open_btn(parent, label, url_fn):
    """url_fn() returns the address to open, or None/'' to do nothing."""
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


class Pager:
    """Wizard frame. pages = [(title, builder)]; builder() fills self.body and returns validate() -> bool.

    route(i) -> index of the page after i, or None to finish (default: i + 1,
    finish after the last page). Back follows the pages actually visited."""

    def __init__(self, root, pages, on_finish, route=None, last_label="마침"):
        self.root, self.pages, self.on_finish = root, pages, on_finish
        self.route = route or (lambda i: i + 1 if i + 1 < len(pages) else None)
        self.last_label = last_label
        self.history, self.validate, self.i = [], None, 0
        self.head = ttk.Label(root, font=("", 11, "bold"), padding=(20, 16, 20, 4))
        self.head.pack(fill="x")
        self.body = ttk.Frame(root, padding=(20, 4, 20, 8))
        self.body.pack(fill="both", expand=True)
        bar = ttk.Frame(root, padding=(20, 8))
        bar.pack(fill="x")
        self.next_btn = ttk.Button(bar, text="다음 →", command=self.go_next)
        self.back_btn = ttk.Button(bar, text="← 이전", command=self.go_back)
        self.next_btn.pack(side="right")
        self.back_btn.pack(side="right", padx=6)

    def show(self, i):
        self.i = i
        for w in self.body.winfo_children():
            w.destroy()
        title, builder = self.pages[i]
        self.head.configure(text=title)
        self.validate = builder()
        self.back_btn.state(["!disabled"] if self.history else ["disabled"])
        self.next_btn.configure(text=self.last_label if self.route(i) is None else "다음 →")

    def go_next(self):
        if not self.validate():
            return
        nxt = self.route(self.i)
        if nxt is None:
            self.on_finish()
            return
        self.history.append(self.i)
        self.show(nxt)

    def go_back(self):
        if self.history:
            self.show(self.history.pop())
