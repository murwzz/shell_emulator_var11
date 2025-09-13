import argparse, base64, csv, os, sys, shlex, tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import datetime as dt
import calendar


@dataclass
class VFSNode:
    name: str
    type: str                 
    owner: str = "root"
    content_b64: Optional[str] = None
    children: Dict[str, "VFSNode"] = field(default_factory=dict)

    def is_dir(self):  return self.type == 'dir'
    def is_file(self): return self.type == 'file'

class VFS:
    def __init__(self, name="vfs"):
        self.name = name
        self.root = VFSNode("/", "dir", "root")

    def _split(self, path: str) -> List[str]:
        path = path.strip()
        if path.startswith("/"):
            path = path[1:]
        return [p for p in path.split("/") if p and p != "."]

    def abspath_parts(self, cwd_parts: List[str], path: str) -> List[str]:
        if not path or path == ".":
            return cwd_parts[:]
        parts = self._split(path) if path.startswith("/") else cwd_parts + self._split(path)
        out = []
        for p in parts:
            if p == "..":
                if out: out.pop()
            else:
                out.append(p)
        return out

    def get(self, cwd_parts: List[str], path: str) -> VFSNode:
        parts = self.abspath_parts(cwd_parts, path)
        cur = self.root
        for p in parts:
            cur = cur.children.get(p)
            if cur is None:
                raise KeyError(f"path not found: /{'/'.join(parts)}")
        return cur

    def listdir(self, node: VFSNode) -> List[VFSNode]:
        if not node.is_dir():
            raise NotADirectoryError("not a directory")
        return [node.children[k] for k in sorted(node.children)]

    def chdir(self, cwd_parts: List[str], path: str) -> List[str]:
        node = self.get(cwd_parts, path)
        if not node.is_dir():
            raise NotADirectoryError("not a directory")
        return self.abspath_parts(cwd_parts, path)

    def _mkdirs(self, parts: List[str]) -> VFSNode:
        cur = self.root
        for p in parts:
            if p not in cur.children:
                cur.children[p] = VFSNode(p, "dir", "root")
            cur = cur.children[p]
            if not cur.is_dir():
                raise ValueError("path conflicts with file")
        return cur

    def add_dir(self, path: str, owner: str):
        node = self._mkdirs(self._split(path))
        node.owner = owner

    def add_file(self, path: str, owner: str, content_b64: Optional[str]):
        parts = self._split(path)
        if not parts: raise ValueError("empty file path")
        dir_parts, fname = parts[:-1], parts[-1]
        d = self._mkdirs(dir_parts)
        d.children[fname] = VFSNode(fname, "file", owner, content_b64 or "")

    @staticmethod
    def from_csv(path: str, name: Optional[str] = None) -> "VFS":
        if not os.path.exists(path) or not os.path.isfile(path):
            raise FileNotFoundError("VFS CSV file not found")
        v = VFS(name or os.path.splitext(os.path.basename(path))[0])
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            need = {"path","type","owner"}
            if not need.issubset(r.fieldnames or []):
                raise ValueError("bad CSV header: need path,type,owner[,content_b64]")
            for i,row in enumerate(r, 2):
                p = (row["path"] or "").strip()
                t = (row["type"] or "").strip()
                o = (row["owner"] or "root").strip()
                c = (row.get("content_b64") or "").strip()
                if not p or t not in ("dir","file"):
                    raise ValueError(f"row {i}: bad values")
                if t == "dir":
                    v.add_dir(p, o)
                else:
                    if c:
                        try: base64.b64decode(c.encode("utf-8"))
                        except Exception: raise ValueError(f"row {i}: content_b64 not valid base64")
                    v.add_file(p, o, c)
        return v

def load_default_vfs() -> VFS:
    v = VFS("default")
    v.add_dir("/home/user","user")
    v.add_file("/home/user/readme.txt","user", base64.b64encode(b"Hello VFS").decode())
    v.add_dir("/etc","root")
    v.add_dir("/var/log","root")
    return v

# --------- оболочка ---------
class Shell:
    def __init__(self, vfs: VFS, user: str | None = None):
        self.vfs = vfs
        self.cwd_parts: List[str] = []
        self.user = user or os.environ.get("USER") or os.environ.get("USERNAME") or "user"

    def parse(self, line):  
        return shlex.split(os.path.expandvars(line), posix=True)

    def run(self, line: str) -> str:
        tokens = self.parse(line.strip())
        if not tokens: return ""
        cmd, *args = tokens
        if cmd == "exit": raise SystemExit
        fn = getattr(self, f"cmd_{cmd}", None)
        if not fn: raise ValueError(f"unknown command: {cmd}")
        return fn(args)

    def cmd_ls(self, args: List[str]) -> str:
        path = args[0] if args else "/" + "/".join(self.cwd_parts)
        node = self.vfs.get(self.cwd_parts, path)
        if node.is_file():
            return node.name
        items = []
        for ch in self.vfs.listdir(node):
            items.append(ch.name + ("/" if ch.is_dir() else ""))
        return "  ".join(items)

    def cmd_cd(self, args: List[str]) -> str:
        if len(args) != 1:
            raise ValueError("cd: expected 1 argument")
        self.cwd_parts = self.vfs.chdir(self.cwd_parts, args[0])
        return ""
    
    def cmd_whoami(self, args: list[str]) -> str:
        if args:
            raise ValueError("whoami: no arguments expected")
        return self.user

    def cmd_cal(self, args: list[str]) -> str:
        # календарь текущего месяца или указанного (YYYY-MM)
        import datetime as dt, calendar
        cal = calendar.TextCalendar()
        if not args:
            today = dt.date.today()
            return cal.formatmonth(today.year, today.month)
        if len(args) == 1 and len(args[0]) == 7 and args[0][4] == "-":
            y, m = args[0].split("-")
            return cal.formatmonth(int(y), int(m))
        raise ValueError("cal: usage: cal [YYYY-MM]")

    def cmd_rev(self, args: list[str]) -> str:
        if not args:
            raise ValueError("rev: usage: rev <text>")
        return " ".join(s[::-1] for s in args)


class App(tk.Tk):
    def __init__(self, shell: Shell):
        super().__init__()
        self.shell = shell
        self.title(f"Shell Emulator — VFS: {shell.vfs.name}")
        self.geometry("820x520")
        self._build_ui()
        self._print_line(f"[ready] VFS='{shell.vfs.name}' cwd='/' user='{shell.user}'")

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.text = tk.Text(self, wrap='word', state='disabled', font=('Menlo', 12))
        self.text.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self.input = ttk.Entry(self)
        self.input.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.input.bind("<Return>", self._on_enter)
        self._update_prompt()

    def _prompt(self) -> str:
        path = '/' + '/'.join(self.shell.cwd_parts)
        return f"{self.shell.vfs.name}:{path}$ "

    def _update_prompt(self):
        p = self._prompt()
        self.input.delete(0, tk.END)
        self.input.insert(0, p)
        self.input.icursor(len(p))

    def _print_line(self, s: str):
        self.text.configure(state='normal')
        self.text.insert(tk.END, s + "\n")
        self.text.see(tk.END)
        self.text.configure(state='disabled')

    def _on_enter(self, _=None):
        full = self.input.get()
        cmd = full.split("$ ", 1)[1] if "$ " in full else full
        self._print_line(full)
        try:
            out = self.shell.run(cmd)
            if out: self._print_line(out)
        except SystemExit:
            self.destroy(); return
        except Exception as e:
            self._print_line(f"error: {e}")
        self._update_prompt()

    def run_script(self, lines):
        for raw in lines:
            line = raw.rstrip("\n")
            if not line.strip(): continue
            self._print_line(self._prompt() + line)
            try:
                out = self.shell.run(line)
                if out: self._print_line(out)
            except SystemExit:
                self.destroy(); return
            except Exception as e:
                self._print_line(f"error: {e}")
                break
        self._update_prompt()

def main(argv=None):
    parser = argparse.ArgumentParser(description="GUI Shell Emulator (stage 3)")
    parser.add_argument("--vfs", help="путь к VFS CSV")
    parser.add_argument("--script", help="путь к стартовому скрипту")
    parser.add_argument("--vfs-name", help="имя VFS в заголовке")
    args = parser.parse_args(argv)

    print(f"[startup] argv={sys.argv} parsed={{'vfs': {args.vfs!r}, 'script': {args.script!r}, 'vfs_name': {args.vfs_name!r}}}")

    try:
        vfs = VFS.from_csv(args.vfs, args.vfs_name) if args.vfs else load_default_vfs()
        if args.vfs_name and not args.vfs:
            vfs.name = args.vfs_name
    except Exception as e:
        messagebox.showerror("VFS load error", f"Failed to load VFS: {e}")
        sys.exit(2)

    app = App(Shell(vfs=vfs))

    if args.script:
        try:
            with open(args.script, encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("Script error", f"Failed to read script: {e}")
            sys.exit(3)
        app.after(200, lambda: app.run_script(lines))

    app.mainloop()

if __name__ == "__main__":
    main()
